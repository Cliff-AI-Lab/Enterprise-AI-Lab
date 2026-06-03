# External Tests

These tests depend on `codesphere-saas` private modules such as `app.services.agent_runner`.
They are intentionally outside the package's default `tests/` path so standalone CI keeps a
clean signal.

Run them explicitly from an environment that has the SaaS repo on `PYTHONPATH`:

```bash
uv run pytest packages/rd-llm-adapter/tests_external
```
