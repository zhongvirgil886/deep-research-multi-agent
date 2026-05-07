import asyncio
import importlib.util
import json
import logging
import os
import pathlib
import shutil
import sys
import unittest
from types import SimpleNamespace


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "backend" / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


from service.deep_research_v2.agents.base import BaseAgent
from service.deep_research_v2.agents.scout import DeepScout
from service.deep_research_v2.agents.wizard import CodeWizard
from service.deep_research_v2.state import create_initial_state
from service.checkpoint_service import CheckpointService


class DummyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Dummy",
            role="test",
            llm_api_key="sk-test",
            llm_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="deepseek-v3.2",
        )

    async def process(self, state):
        return state


def load_demo_runner_module():
    script = APP_ROOT / "scripts" / "test_deep_research_v2.py"
    spec = importlib.util.spec_from_file_location("deep_research_v2_demo_runner", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DemoEnvLoadingTests(unittest.TestCase):
    def test_load_demo_env_reads_env_file_without_overwriting_existing_values(self):
        module = load_demo_runner_module()

        old_dashscope = os.environ.get("DASHSCOPE_API_KEY")
        old_bocha = os.environ.get("BOCHA_API_KEY")
        self.addCleanup(self._restore_env, "DASHSCOPE_API_KEY", old_dashscope)
        self.addCleanup(self._restore_env, "BOCHA_API_KEY", old_bocha)

        os.environ["DASHSCOPE_API_KEY"] = "already-set"
        os.environ.pop("BOCHA_API_KEY", None)

        env_path = REPO_ROOT / "tests" / "fixtures" / "deep_research_demo.env"
        env_path.write_text(
            "DASHSCOPE_API_KEY=from-file\nBOCHA_API_KEY=bocha-from-file\n",
            encoding="utf-8",
        )
        self.addCleanup(lambda: env_path.unlink(missing_ok=True))

        module.load_demo_env(env_path)

        self.assertEqual(os.environ["DASHSCOPE_API_KEY"], "already-set")
        self.assertEqual(os.environ["BOCHA_API_KEY"], "bocha-from-file")

    @staticmethod
    def _restore_env(key, value):
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


class DemoRunnerExitTests(unittest.IsolatedAsyncioTestCase):
    async def test_trace_text_replaces_emoji_status_symbols_with_ascii_labels(self):
        module = load_demo_runner_module()

        formatted = module._format_trace_text("✅ 通过 ❌ 失败 ⚠️ 注意 🔍 搜索")

        self.assertEqual(formatted, "[OK] 通过 [FAIL] 失败 [WARN] 注意 [SEARCH] 搜索")

    async def test_main_returns_nonzero_when_agent_checks_fail(self):
        module = load_demo_runner_module()

        async def fake_individual_agents():
            return False

        async def fake_full_workflow():
            raise AssertionError("full workflow should be skipped")

        module.test_individual_agents = fake_individual_agents
        module.test_full_workflow = fake_full_workflow

        self.assertEqual(await module.main(), 1)

    async def test_main_returns_nonzero_when_e2e_fails(self):
        module = load_demo_runner_module()

        async def fake_individual_agents():
            return True

        async def fake_full_workflow():
            return False

        module.test_individual_agents = fake_individual_agents
        module.test_full_workflow = fake_full_workflow

        self.assertEqual(await module.main(), 1)

    async def test_main_returns_zero_when_all_checks_pass(self):
        module = load_demo_runner_module()

        async def fake_individual_agents():
            return True

        async def fake_full_workflow():
            return True

        module.test_individual_agents = fake_individual_agents
        module.test_full_workflow = fake_full_workflow

        self.assertEqual(await module.main(), 0)

    def test_is_successful_research_result_rejects_empty_report(self):
        module = load_demo_runner_module()

        self.assertFalse(
            module.is_successful_research_result(
                phases_seen={"planning", "researching", "analyzing", "writing", "reviewing"},
                events=[
                    {
                        "type": "research_complete",
                        "final_report": "",
                        "quality_score": 0.0,
                        "facts_count": 22,
                        "charts_count": 7,
                    }
                ],
                error_count=0,
            )
        )

    def test_is_successful_research_result_accepts_nonempty_report(self):
        module = load_demo_runner_module()

        self.assertTrue(
            module.is_successful_research_result(
                phases_seen={"planning", "researching", "analyzing", "writing", "reviewing"},
                events=[
                    {
                        "type": "research_complete",
                        "final_report": "valid report body",
                        "quality_score": 7.5,
                        "facts_count": 3,
                        "charts_count": 1,
                    }
                ],
                error_count=0,
            )
        )

    async def test_run_with_timeout_returns_nonzero_when_coroutine_times_out(self):
        module = load_demo_runner_module()

        async def slow_check():
            await asyncio.sleep(0.05)
            return True

        self.assertEqual(await module.run_with_timeout(slow_check(), 0.01, "slow"), 1)

    async def test_run_with_timeout_preserves_success_exit_code(self):
        module = load_demo_runner_module()

        async def fast_check():
            return 0

        self.assertEqual(await module.run_with_timeout(fast_check(), 1.0, "fast"), 0)


class TokenClampTests(unittest.IsolatedAsyncioTestCase):
    async def test_call_llm_clamps_dashscope_max_tokens_before_api_call(self):
        asyncio.get_running_loop().slow_callback_duration = 1.0
        agent = DummyAgent()
        captured_kwargs = {}

        class FakeCompletions:
            def create(self, **kwargs):
                captured_kwargs.update(kwargs)
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content='{"ok": true}')
                        )
                    ]
                )

        agent.client = SimpleNamespace(
            chat=SimpleNamespace(completions=FakeCompletions())
        )

        await agent.call_llm("system", "user", max_tokens=16000)

        self.assertEqual(captured_kwargs["max_tokens"], 8192)


class DeepScoutBudgetTests(unittest.IsolatedAsyncioTestCase):
    async def test_deep_search_stops_when_global_budget_is_exhausted(self):
        scout = object.__new__(DeepScout)
        scout.name = "DeepScout"
        scout.logger = logging.getLogger("test.DeepScout")
        scout.fact_fingerprints = {}
        scout.max_deep_search_calls = 1

        search_calls = []

        async def fake_execute_search(query, count=6):
            search_calls.append(query)
            return [
                {
                    "title": f"title {query}",
                    "site_name": "source",
                    "url": f"https://example.test/{query}",
                    "summary": "summary",
                }
            ]

        async def fake_analyze_deep_search_results(*args, **kwargs):
            return {
                "extracted_facts": [
                    {
                        "content": "fact",
                        "source_url": "https://example.test/fact",
                        "source_name": "source",
                    }
                ],
                "data_points": [],
                "further_tracing_queries": ["next-query"],
            }

        scout._execute_search = fake_execute_search
        scout._analyze_deep_search_results = fake_analyze_deep_search_results

        state = create_initial_state("query", "session")
        await scout._execute_deep_search(
            state,
            section_id="sec_1",
            queries=["first-query", "second-query"],
            search_type="follow_up",
            hypotheses=[],
            max_depth=2,
        )

        self.assertEqual(search_calls, ["first-query"])
        self.assertEqual(state["_deep_search_calls"], 1)


class DeepScoutNormalizationTests(unittest.TestCase):
    def test_duplicate_fact_handles_list_fields_from_llm(self):
        scout = object.__new__(DeepScout)
        scout.logger = logging.getLogger("test.DeepScout")
        scout.fact_fingerprints = {}

        self.assertFalse(
            scout._is_duplicate_fact(
                ["新能源汽车销量增长", "市场规模扩大"],
                ["https://example.test/a", "https://example.test/b"],
            )
        )

    def test_knowledge_graph_handles_list_entity_names_from_llm(self):
        scout = object.__new__(DeepScout)
        scout.logger = logging.getLogger("test.DeepScout")
        state = create_initial_state("query", "session")

        scout._update_knowledge_graph(
            state,
            [
                {
                    "name": ["比亚迪", "BYD"],
                    "type": ["company"],
                    "relations": ["竞争者", ["供应链", "电池"]],
                }
            ],
        )

        self.assertEqual(state["knowledge_graph"]["nodes"][0]["name"], "比亚迪; BYD")
        self.assertEqual(
            [edge["relation"] for edge in state["knowledge_graph"]["edges"]],
            ["竞争者", "供应链; 电池"],
        )


class CodeWizardDebugPathTests(unittest.TestCase):
    def test_debug_session_dir_uses_configured_writable_base_path(self):
        wizard = object.__new__(CodeWizard)
        wizard.logger = logging.getLogger("test.CodeWizard")

        old_debug_dir = os.environ.get("CODEWIZARD_DEBUG_DIR")
        self.addCleanup(DemoEnvLoadingTests._restore_env, "CODEWIZARD_DEBUG_DIR", old_debug_dir)

        debug_base = REPO_ROOT / "tests" / "fixtures" / "codewizard_debug"
        os.environ["CODEWIZARD_DEBUG_DIR"] = str(debug_base)

        wizard._save_debug_log("step", "content")

        session_dir = pathlib.Path(wizard._debug_session_dir)
        self.assertTrue(session_dir.is_relative_to(debug_base))
        self.assertTrue((session_dir / "step.txt").exists())
        self.addCleanup(lambda: shutil.rmtree(debug_base, ignore_errors=True))


class CodeWizardCleanCodeTests(unittest.TestCase):
    def test_clean_code_converts_backslash_prefixed_statement_to_newline(self):
        wizard = object.__new__(CodeWizard)

        cleaned = wizard._clean_code(
            "sns.set_theme(style='whitegrid')\\data = {'Year': [2024]}\\ndf = pd.DataFrame(data)"
        )

        self.assertIn("sns.set_theme(style='whitegrid')\ndata =", cleaned)
        compile(cleaned, "<cleaned>", "exec")


class CodeWizardExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_execute_code_returns_before_sandbox_when_syntax_is_invalid(self):
        wizard = object.__new__(CodeWizard)
        wizard.logger = logging.getLogger("test.CodeWizard")

        old_debug_dir = os.environ.get("CODEWIZARD_DEBUG_DIR")
        self.addCleanup(DemoEnvLoadingTests._restore_env, "CODEWIZARD_DEBUG_DIR", old_debug_dir)
        debug_base = REPO_ROOT / "tests" / "fixtures" / "codewizard_invalid"
        os.environ["CODEWIZARD_DEBUG_DIR"] = str(debug_base)
        self.addCleanup(lambda: shutil.rmtree(debug_base, ignore_errors=True))

        def fail_if_called(_code):
            raise AssertionError("sandbox should not run invalid code")

        wizard._execute_in_sandbox = fail_if_called

        result = await wizard._execute_code("data = {'Year': [2024]\n")

        self.assertFalse(result["success"])
        self.assertIn("Syntax error", result["error"])
        self.assertEqual(result["charts"], [])


class CheckpointSerializationTests(unittest.TestCase):
    def test_clean_state_removes_runtime_queue_and_is_json_serializable(self):
        service = CheckpointService()
        queue = asyncio.Queue()

        cleaned = service._clean_state_for_storage(
            {
                "query": "q",
                "_message_queue": queue,
                "nested": {"queue": queue, "value": 1},
            }
        )

        self.assertNotIn("_message_queue", cleaned)
        json.dumps(cleaned)
        self.assertEqual(cleaned["nested"]["value"], 1)
        self.assertIsInstance(cleaned["nested"]["queue"], str)


if __name__ == "__main__":
    unittest.main()
