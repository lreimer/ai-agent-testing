.DEFAULT_GOAL := help

UV ?= uv
MVN ?= mvn
NPM ?= npm
DOCKER ?= docker

.PHONY: help setup setup-python setup-node build docker-build docker-build-evals run test demos demo-deepeval demo-ragas demo-promptfoo k8s-secret k8s-evals-secret testworkflow

help:
	@printf '%s\n' \
		'make setup          Install locked Python and Node dependencies' \
		'make build          Install dependencies and package the Java targets' \
		'make docker-build   Build the agent Docker image as ai-agent-testing:local' \
		'make docker-build-evals Build the tests/demos image as ai-agent-testing-evals:local' \
		'make run            Start the local Java ADK server (Gemini key required)' \
		'make test           Run offline contract tests with console results' \
		'make demo-deepeval  Run live DeepEval tests (server and judge key required)' \
		'make demo-ragas     Run live RAGAS tests (server and judge key required)' \
		'make demo-promptfoo Run PromptFoo with its console results table (server required)' \
		'make k8s-secret     Create the Kubernetes secret from GOOGLE_API_KEY' \
		'make k8s-evals-secret Create the Testkube judge secret from OPENAI_API_KEY' \
		'make testworkflow   Apply and run the Testkube TestWorkflow' \
		'make demos          Run all three live demos sequentially'

setup: setup-python setup-node

setup-python:
	$(UV) sync --locked

setup-node:
	$(NPM) ci

build: setup
	$(MVN) -f agents/pom.xml package

docker-build:
	$(DOCKER) build -f agents/Dockerfile -t ai-agent-testing:local .

docker-build-evals:
	$(DOCKER) build -f evals/Dockerfile -t ai-agent-testing-evals:local .

run:
	GOOGLE_GENAI_USE_VERTEXAI=false $(MVN) -f agents/pom.xml compile exec:java

test:
	RUN_LIVE_EVALS=0 $(UV) run --locked python -m pytest -v -s -rA

demo-deepeval:
	RUN_LIVE_EVALS=1 DEEPEVAL_VERBOSE_MODE=1 $(UV) run --locked python -m pytest evals/test_deepeval.py -v -s -rA

demo-ragas:
	RUN_LIVE_EVALS=1 $(UV) run --locked python -m pytest evals/test_ragas.py -v -s -rA

demo-promptfoo:
	PYTHONPATH="$(CURDIR)$${PYTHONPATH:+:$$PYTHONPATH}" \
		PROMPTFOO_DISABLE_TELEMETRY=1 \
		$(UV) run --locked $(NPM) run eval:promptfoo -- --table

k8s-secret:
	: "$${GOOGLE_API_KEY:?...Set GOOGLE_API_KEY in your environment first}"
	kubectl create secret generic ai-agent-testing --from-literal="GOOGLE_API_KEY=$$GOOGLE_API_KEY"

k8s-evals-secret:
	: "$${OPENAI_API_KEY:?...Set OPENAI_API_KEY in your environment first}"
	printf '%s' "$$OPENAI_API_KEY" | kubectl create secret generic ai-agent-testing-evals \
		--namespace testkube --from-file=OPENAI_API_KEY=/dev/stdin

deploy:
	@kubectl apply -f agents/k8s/deployment.yaml
	@kubectl apply -f agents/k8s/service.yaml

testworkflow:
	@kubectl apply -f agents/k8s/testworkflow.yaml
	testkube run testworkflow ai-agent-testing --namespace testkube --watch

demos:
	$(MAKE) demo-deepeval
	$(MAKE) demo-ragas
	$(MAKE) demo-promptfoo
