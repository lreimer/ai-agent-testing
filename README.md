# ai-agent-testing
AI Testing Beyond the Basics: Ensuring Truthful and Reliable Chatbots and Agents Demos

Two **Google ADK Java** targets share a deliberately small, fictional conference FAQ:

- `chatbot`: an `LlmAgent` with the FAQ in its instructions; no tools.
- `conference_agent`: an `LlmAgent` that calls `lookupConference` to retrieve facts.
  Unknown topics return no context; the agent should admit it does not know.

All evaluation code and assertions are **Python**. PromptFoo uses its Node CLI
to orchestrate a Python provider and Python assertions.

| Demo | What it checks |
| --- | --- |
| DeepEval | Answer relevance, faithfulness, and tool names/arguments |
| RAGAS | Faithfulness against context actually returned by the agent's tool |
| PromptFoo | Known facts, tool use, unknown facts, and instruction override regression |

## Setup

Use Java 17+, Maven 3.9+, Python 3.12, [uv](https://docs.astral.sh/uv/getting-started/installation/),
Node.js 22+ (24 recommended), and Make.
Run the following from the repository root:

```bash
make build
```

`make build` runs `uv sync --locked`, `npm ci`, and the Maven package build.
uv manages `.venv` automatically; no activation is needed. Python dependencies
are declared in `pyproject.toml` and resolved in the committed `uv.lock`.
The Python dependency pins keep RAGAS's legacy imports compatible.
PromptFoo 0.116.7 is pinned for its Python provider and local SQLite support.
`.npmrc` omits optional dependencies that these demos do not need. The npm
overrides select patched transitive dependencies; the Python-provider path is
the supported demo integration.

## Run the Java targets

Supply credentials through the environment, never source files. ADK uses
`GOOGLE_API_KEY` for Gemini; obtain one from Google AI Studio. In the server terminal:

```bash
read -rsp "Gemini API key: " GOOGLE_API_KEY; echo
export GOOGLE_API_KEY
export GOOGLE_GENAI_USE_VERTEXAI=false
export ADK_MODEL=gemini-flash-latest
make run
```

Open <http://127.0.0.1:8000> for the ADK development UI and select either target.
The server binds only to loopback, uses an explicit CORS allowlist, and stores
sessions in memory. **It is an unauthenticated local demo, not a production server.**
Do not expose or port-forward it to untrusted networks. `ADK_PORT` changes its port.

In a second terminal:

```bash
curl http://127.0.0.1:8000/list-apps
uv run --locked python -c 'from evals.adk_client import ask; print(ask("conference_agent", "When is the keynote?"))'
```

The Python adapter creates a fresh session for each question, captures the final
answer, tool calls, and retrieved contexts from `/run`, then deletes the session.
Set `ADK_BASE_URL` if you change the server port.

## Run the demos

Run `make help` for all targets. `make setup` installs only dependencies.
`make demos` runs all three live demos sequentially, stopping on failure;
start the server separately and provide the credentials described below first.
Python test targets use verbose output with capture disabled (`-v -s -rA`),
so test outcomes and evaluation output appear directly on the console.
DeepEval verbose metric reporting is enabled; RAGAS prints each faithfulness
score, and PromptFoo explicitly prints its results table. Failed evaluations
return a nonzero exit status.

### Offline contract tests (no keys or server required)

```bash
make test
```

This tests event parsing, error handling, session cleanup, and the PromptFoo
Python provider/assertions. Live evaluation tests are skipped by default.

### DeepEval

With the Java server running, provide an OpenAI key for the evaluation judge:

```bash
read -rsp "OpenAI judge API key: " OPENAI_API_KEY; echo
export OPENAI_API_KEY
export JUDGE_MODEL=gpt-4o-mini
make demo-deepeval
```

### RAGAS

Uses the same server and OpenAI judge credentials:

```bash
make demo-ragas
```

The retrieval demo is intentionally a tiny topic lookup, not a vector database.
Scores use **observed tool context**, not copied expected answers. Missing
retrieval fails the test rather than silently scoring fabricated evidence.

### PromptFoo

Requires the running Java server and Gemini key, but no OpenAI judge.
From the repository root:

```bash
make demo-promptfoo
```

The config lives in `evals/promptfoo/promptfooconfig.yaml`; providers and
assertions are Python files alongside it. `--no-cache` ensures each evaluation
exercises the Java targets. Results are local; do not use PromptFoo's share
option with private prompts or outputs.

## Conference walkthrough

1. Ask both targets “When and where is the keynote?” (09:00, Hall A).
2. Ask the agent about the workshop (14:00, Room B, bring a laptop);
   inspect its `lookupConference` call in the UI.
3. Ask for an unknown WiFi password; discuss abstention versus hallucination.
4. Run the three demos and contrast deterministic Python assertions with
   LLM-based grading and tool-call checks.
5. Try the schedule-override prompt in PromptFoo and discuss why prompt
   instructions alone are not a security boundary.

Live calls cost money, need network access and model quota, and can produce
non-deterministic results. A failing live evaluation is useful demo evidence,
not necessarily a broken test harness. Offline tests do not validate model quality.

## Maintainer

M.-Leander Reimer (@lreimer), <mario-leander.reimer@qaware.de>

## License

This software is provided under the MIT open source license, read the `LICENSE` file for details.
