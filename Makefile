.DEFAULT_GOAL := help

UV ?= uv
MVN ?= mvn
NPM ?= npm

.PHONY: help setup setup-python setup-node build run test demos demo-deepeval demo-ragas demo-promptfoo

help:
	@printf '%s\n' \
		'make setup          Install locked Python and Node dependencies' \
		'make build          Install dependencies and package the Java targets' \
		'make run            Start the local Java ADK server (Gemini key required)' \
		'make test           Run offline contract tests with console results' \
		'make demo-deepeval  Run live DeepEval tests (server and judge key required)' \
		'make demo-ragas     Run live RAGAS tests (server and judge key required)' \
		'make demo-promptfoo Run PromptFoo with its console results table (server required)' \
		'make demos          Run all three live demos sequentially'

setup: setup-python setup-node

setup-python:
	$(UV) sync --locked

setup-node:
	$(NPM) ci

build: setup
	$(MVN) -f agents/pom.xml package

run:
	GOOGLE_GENAI_USE_VERTEXAI=false $(MVN) -f agents/pom.xml compile exec:java

test:
	RUN_LIVE_EVALS=0 $(UV) run --locked python -m pytest -v -s -rA

demo-deepeval:
	RUN_LIVE_EVALS=1 DEEPEVAL_VERBOSE_MODE=1 $(UV) run --locked python -m pytest evals/test_deepeval.py -v -s -rA

demo-ragas:
	RUN_LIVE_EVALS=1 $(UV) run --locked python -m pytest evals/test_ragas.py -v -s -rA

demo-promptfoo: setup-python setup-node
	PYTHONPATH="$(CURDIR)$${PYTHONPATH:+:$$PYTHONPATH}" \
		PROMPTFOO_PYTHON="$(CURDIR)/.venv/bin/python" \
		PROMPTFOO_DISABLE_TELEMETRY=1 \
		$(NPM) run eval:promptfoo -- --table

demos:
	$(MAKE) demo-deepeval
	$(MAKE) demo-ragas
	$(MAKE) demo-promptfoo
