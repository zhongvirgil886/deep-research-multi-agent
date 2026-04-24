# Update Rules

> Strict rules for incremental updates to project files. Used by `/save` to ensure safe multi-window collaboration.

## Core Principles

1. **Single Source of Truth** — Only project-level files are maintained. Git is the collaboration foundation. Pull before updating.
2. **Incremental Updates** — Read latest first, update based on "latest content + current session context". Never regenerate whole files. Show diff before commit.
3. **Structured Sections** — Different windows update different module sections to reduce conflicts.
4. **Interactive Confirmation** — Always show diff, provide options (confirm / view / edit / cancel), commit only after approval.

---

## checkpoint.md Rules

### Mandatory

1. **Module Section Structure**
   - Level 1 heading: `## <模块名>模块`
   - Do not delete / modify other module sections
   - Add items only under your responsible module

2. **Fixed Template** per module:
   ```
   **负责**：<owner>
   **状态**：<status>
   **测试状态**：⚠️ / ✅
   **分支**：<branch>
   **最后更新**：<date>

   ### 最近完成
   ### 进行中
   ### 下一步
   ### 依赖
   ### 相关文档
   ```

3. **Global Status Table** — update only your row, preserve others.

4. **「最近完成」cap at 10 items** — older items → `docs/archive/checkpoint-history.md`.

### Forbidden

- Delete other module sections
- Modify other module content
- Reorganize heading levels
- Merge sections

---

## docs/**/index.md Rules

- Any `.md` created under `docs/<subdir>/` MUST be registered in that subdir's `index.md`
- Row format: `| 文档 | 路径 | 描述 | 更新日期 |`
- Never create fragmented docs; prefer extending existing entries

---

## CLAUDE.md / AGENTS.md Rules

**RARE updates.** These are the project "constitution".

- Propose change first, don't commit directly
- Explain why, show diff
- Get user consensus before merging
- Document change reason in commit message

Forbidden: casual changes, removing existing rules without discussion.

---

## Conflict Resolution

1. `git pull` first
2. Auto-merge success → verify → proceed
3. Conflict → stop, alert user, show markers, offer: manual / abort / branch

### Prevention

- Work on separate modules = separate sections
- Pull frequently
- Run `/load` before starting

---

## Safety Checks

### Before Commit

- ✅ Only intended sections modified
- ✅ No other content deleted
- ✅ Structure preserved
- ✅ Diff reviewed with user

### After Commit

- `git push` to share
- Display commit hash
- Notify team for significant changes
