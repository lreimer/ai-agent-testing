# AI Agent Testing
AI Testing Beyond the Basics: Ensuring Truthful and Reliable Chatbots and Agents Demos

Two **Google ADK Java** targets share a deliberately small conference FAQ:

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

# or alternatively
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
npm ci
mvn -f agents/pom.xml package
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

# or alternatively
mvn -f agents/pom.xml compile exec:java
```

Open <http://127.0.0.1:8000> for the ADK development UI and select either target.
The server binds only to loopback, uses an explicit CORS allowlist, and stores
sessions in memory. **It is an unauthenticated local demo, not a production server.**
Do not expose or port-forward it to untrusted networks. `ADK_PORT` changes its port.

In a second terminal:

```bash
curl http://127.0.0.1:8000/list-apps
uv run --locked python -c 'from evals.adk_client import ask; print(ask("conference_agent", "When is the keynote?"))'

# or alternatively
python -c 'from evals.adk_client import ask; print(ask("conference_agent", "When is the keynote?"))'
```

The Python adapter creates a fresh session for each question, captures the final
answer, tool calls, and retrieved contexts from `/run`, then deletes the session.
Set `ADK_BASE_URL` if you change the server port.

## Run with Docker

Build from the repository root (Docker with BuildKit required):

```bash
docker build -t ai-agent-testing:local .
```

The multi-stage build uses Maven and Java 17, then copies only the application
JAR and runtime dependencies into a **Distroless Java 17** image. The runtime
runs as non-root (UID/GID 65532), with no shell, package manager, Maven, Python,
or Node.js. Local build outputs and credentials are excluded from the build
context. No local Java or Maven installation is needed.

With `GOOGLE_API_KEY` exported as described above:

```bash
docker run --rm --name ai-agent-testing \
  -p 127.0.0.1:8000:8000 \
  -e GOOGLE_API_KEY \
  -e ADK_MODEL=gemini-flash-latest \
  ai-agent-testing:local
```

Open <http://127.0.0.1:8000> or check the API from another terminal:

```bash
curl --fail http://127.0.0.1:8000/list-apps
docker stop ai-agent-testing
```

The image sets `ADK_HOST=0.0.0.0` so Docker port publishing works; non-container
runs still default to `127.0.0.1`. Keep the host-side port bound to loopback as
shown: this remains an unauthenticated demo, not a production deployment.
Credentials are supplied only at runtime, never baked into the image.
To use another host port, for example 9000, publish
`-p 127.0.0.1:9000:8000` and set `ADK_BASE_URL=http://127.0.0.1:9000`
when running the evaluation clients on the host.

## Run on Kubernetes

The manifests in [k8s/](k8s/) deploy one replica of `ai-agent-testing:local`
and an internal `ClusterIP` Service on port 8000. Build the image as above and
make it available to your cluster's container runtime (for example,
`kind load docker-image ai-agent-testing:local` for kind). For a remote cluster,
push the image to your registry and update `image` in
[k8s/deployment.yaml](k8s/deployment.yaml) to that registry reference.

Create the required Secret in the same namespace as the Deployment, using
the exported `GOOGLE_API_KEY`, then apply the manifests:

```bash
printenv GOOGLE_API_KEY | kubectl create secret generic ai-agent-testing \
  --from-file=GOOGLE_API_KEY=/dev/stdin
kubectl apply -f k8s/
kubectl rollout status deployment/ai-agent-testing
kubectl port-forward --address 127.0.0.1 service/ai-agent-testing 8000:8000
```

Ensure `GOOGLE_API_KEY` is exported and non-empty before creating the Secret.
Do not commit credentials or generated Secret YAML. Open
<http://127.0.0.1:8000> or run `curl --fail http://127.0.0.1:8000/list-apps`
in another terminal. Stop port-forwarding with Ctrl-C.

The Deployment runs non-root with a read-only root filesystem and a writable
temporary volume. Startup, readiness, and liveness probes use `/list-apps`
without making paid model calls. CPU and memory requests/limits are initial
demo defaults; tune them for your workload. Sessions remain in memory and are
lost on Pod restarts or replacement; keep a single replica for this demo.
The Service does not expose the app outside the cluster, but other cluster
workloads can reach it. Use only a trusted demo cluster; there is still no
authentication. No Ingress or public LoadBalancer is provided.

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

# or alternatively
python -m pytest
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

# or alternatively
RUN_LIVE_EVALS=1 python -m pytest evals/test_deepeval.py -v
```

### RAGAS

Uses the same server and OpenAI judge credentials:

```bash
make demo-ragas

# or alternatively
RUN_LIVE_EVALS=1 python -m pytest evals/test_ragas.py -v
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

Ask either target "When and where is Mario-Leander Reimer's TestCon session?"
The agent should retrieve the `session` topic and answer with the details above.
For the separate fictional FAQ demonstration:

1. Ask both targets “When and where is the keynote?” (09:00, Hall A).
2. Ask the agent about the workshop (14:00, Room B, bring a laptop);
   inspect its `lookupConference` call in the UI.
3. Ask for the WiFi password; the agent should say the hotel's open WiFi network
   does not require one.
4. Ask about an unknown topic such as parking; discuss abstention versus hallucination.
5. Run the three demos and contrast deterministic Python assertions with
   LLM-based grading and tool-call checks.
6. Try the schedule-override prompt in PromptFoo and discuss why prompt
   instructions alone are not a security boundary.

Live calls cost money, need network access and model quota, and can produce
non-deterministic results. A failing live evaluation is useful demo evidence,
not necessarily a broken test harness. Offline tests do not validate model quality.

## Maintainer

M.-Leander Reimer (@lreimer), <mario-leander.reimer@qaware.de>

## License

This software is provided under the MIT open source license, read the `LICENSE` file for details.
