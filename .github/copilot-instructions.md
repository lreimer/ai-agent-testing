# Repository instructions

## Architecture

- `agents/src/main/java/dev/lreimer/testing/AgentServer.java` is the Java 17 Google ADK backend. It defines two apps: `chatbot` answers from facts embedded in its instructions, while `conference_agent` calls `lookupConference` and grounds answers in the returned contexts. The FAQ facts and tool response shape are defined together in this class.
- The backend is exposed through the ADK development server on port 8000. `evals/adk_client.py` is the shared Python adapter: each `ask()` creates a fresh session, posts a non-streaming request to `/run`, extracts the answer and actual tool evidence from events, and deletes the session.
- Python owns the evaluation suites. DeepEval checks answer relevance, faithfulness, and tool selection; RAGAS scores faithfulness against contexts actually returned by the tool; PromptFoo runs a Python provider and Python assertions against both Java apps. PromptFoo config and implementation are colocated in `evals/promptfoo/`.
- Offline contract tests are in `tests/`; model-backed evaluations are in `evals/` and are marked `live`. The backend is also packaged as a Docker image and has Kubernetes manifests under `agents/`.
- `.mcp.json` provides an optional Playwright MCP server for browser-based checks of the ADK development UI; it is separate from the Python/Java build and test dependencies.

## Build and test

Run commands from the repository root. `make build` installs the locked Python and Node dependencies and packages the Java app; `make setup` installs dependencies only.

```bash
make build
make test
```

Run one offline test or a whole test file with pytest:

```bash
RUN_LIVE_EVALS=0 uv run --locked python -m pytest tests/test_adk_client.py::test_fresh_session_and_cleanup -v -s -rA
RUN_LIVE_EVALS=0 uv run --locked python -m pytest tests/test_adk_client.py -v -s -rA
```

Live evaluations require the Java server to be running (`make run`) and the credentials described in `README.md`. Run a suite with `make demo-deepeval`, `make demo-ragas`, or `make demo-promptfoo`; `make demos` runs all three. These call real models and may incur cost. To invoke one live pytest directly, set `RUN_LIVE_EVALS=1`, for example:

```bash
RUN_LIVE_EVALS=1 uv run --locked python -m pytest evals/test_ragas.py::test_retrieved_context_faithfulness -v
```

`make docker-build` builds the container image. There is no separate configured lint command.

## Repository-specific conventions

- Keep the Java FAQ facts in `AgentServer.FACTS` and keep the app instructions/tool topic guidance consistent with them. Unknown tool topics return `not_found` with empty contexts; do not substitute expected fixture text for missing retrieval.
- Evaluation evidence must come from the real ADK event stream. `parse_events()` ignores thought text, uses the final model response, records function calls and returned contexts, and raises on failed runs or missing answers. Preserve session deletion in `ask()` even when a request fails.
- DeepEval's chatbot case has no retrieval tool, so it supplies its known embedded fact as evaluation context; the `conference_agent` and RAGAS cases require non-empty contexts returned by the tool. PromptFoo assertions inspect actual tool-call metadata when tool use is part of a test.
- Keep offline tests independent of a running server and model credentials. Live tests use the `live` pytest marker and are skipped unless `RUN_LIVE_EVALS=1`.
- Keep credentials in environment variables and out of source/config files. The local ADK server is an unauthenticated demo and should remain bound to loopback for local use.
