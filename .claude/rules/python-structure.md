---
paths:
  - "backend/**/*.py"
---

# Python Structure Rules (backend/)

- 所有后端 Python 业务代码必须放在 `backend/app/` 下
- `backend/` 根层（`backend/app/` 以外）出现 `.py` 文件视为异常，须说明原因
  - 允许例外：`backend/conftest.py`、`backend/setup.py`
- 新增模块放 `backend/app/<最近相关目录>/`，不得在 `backend/app/` 顶层直接放业务 `.py`
- 测试镜像源码：`backend/app/core/config.py` → `backend/test/core/test_config.py`
- 根目录只允许：`AGENTS.md`、`CLAUDE.md`、`README.md`、`checkpoint.md`、`.gitignore`、`docker-compose.yml`、`start-services.sh`、`pyproject.toml`（如有）
- 不在项目根创建 `src/` 目录（backend 自持布局，避免并行结构）
