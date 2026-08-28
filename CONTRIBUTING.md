# Contributing to Agentic-GraphRAG-Blueprint

Thank you for your interest in contributing! Please follow these simple steps:

### Contribution Steps
1. **Create a Branch**: Use a descriptive name like `feature/incremental-ingestion` or `fix/azure-openai-endpoint`.

2. **Commit Changes**: Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) (e.g., `feat: add local search routing`).

3. **Verify**:
   - Backend: `python -m py_compile app.py` (from `backend/`) and add tests for any new logic.
   - Frontend: `npm run build` (from `frontend/`).
   - Infrastructure: `terraform fmt -check` and `terraform validate` (from `infrastructure/terraform/`).

4. **Push and Open a PR**: Provide a clear description of what your changes achieve.
