"""DeepEval: answer relevance, grounding, and actual agent tool selection."""

import os

import pytest

from evals.adk_client import ask

pytestmark = pytest.mark.live


@pytest.mark.parametrize("app", ["chatbot", "conference_agent"])
def test_grounded_conference_answer(app):
    from deepeval import assert_test
    from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
    from deepeval.test_case import LLMTestCase

    question = "When and where is the keynote?"
    result = ask(app, question)
    contexts = result["contexts"] if app == "conference_agent" else [
        "The keynote starts at 09:00 in Hall A."
    ]
    assert contexts, "The agent must retrieve context before answering"
    model = os.environ.get("JUDGE_MODEL", "gpt-4o-mini")
    case = LLMTestCase(
        input=question, actual_output=result["answer"], retrieval_context=contexts,
    )
    assert_test(case, [
        AnswerRelevancyMetric(threshold=0.8, model=model),
        FaithfulnessMetric(threshold=0.8, model=model),
    ])


def test_agent_tool_selection():
    from deepeval import assert_test
    from deepeval.metrics import ToolCorrectnessMetric
    from deepeval.test_case import LLMTestCase, ToolCall, ToolCallParams

    question = "What should I bring to the AI testing workshop?"
    result = ask("conference_agent", question)
    case = LLMTestCase(
        input=question,
        actual_output=result["answer"],
        tools_called=[
            ToolCall(name=call["name"], input_parameters=call.get("args", {}))
            for call in result["tool_calls"]
        ],
        expected_tools=[ToolCall(name="lookupConference", input_parameters={"topic": "workshop"})],
    )
    assert_test(case, [ToolCorrectnessMetric(
        threshold=1.0, evaluation_params=[ToolCallParams.INPUT_PARAMETERS],
        model=os.environ.get("JUDGE_MODEL", "gpt-4o-mini"),
    )])
