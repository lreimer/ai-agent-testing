from unittest.mock import patch

import pytest

from evals.adk_client import ask, parse_events
from evals.promptfoo.assertions import admits_unknown, get_assert, used_tool
from evals.promptfoo.provider import call_api


def event(*parts, role="model"):
    return {"content": {"role": role, "parts": list(parts)}}


def test_extracts_final_answer_and_real_retrieval():
    events = [
        event({"text": "Private reasoning", "thought": True}),
        event({"text": "Let me check"}, {
            "functionCall": {"name": "lookupConference", "args": {"topic": "keynote"}}
        }),
        event({"functionResponse": {
            "name": "lookupConference",
            "response": {"contexts": ["The keynote starts at 09:00 in Hall A."]},
        }}, role="user"),
        event({"text": "09:00"}, {"text": " in Hall A."}),
    ]
    result = parse_events(events)
    assert result["answer"] == "09:00 in Hall A."
    assert result["tool_calls"] == [
        {"name": "lookupConference", "args": {"topic": "keynote"}}
    ]
    assert result["contexts"] == ["The keynote starts at 09:00 in Hall A."]


@pytest.mark.parametrize("events", [
    [], [{"content": None}], [event({"text": "Question"}, role="user")],
    [event({"text": "Reasoning", "thought": True})],
    [{"errorMessage": "Quota exceeded"}], [{"errorCode": "MODEL_ERROR"}],
])
def test_rejects_missing_or_failed_answers(events):
    with pytest.raises(RuntimeError):
        parse_events(events)


def test_fresh_session_and_cleanup():
    with patch("evals.adk_client._request", side_effect=[
        {"id": "session-1"}, [event({"text": "Hello"})], None,
    ]) as request:
        assert ask("chatbot", "Hi")["answer"] == "Hello"
    assert request.call_args_list[0].args == (
        "POST", "/apps/chatbot/users/python-eval/sessions", {"state": {}},
    )
    payload = request.call_args_list[1].args[2]
    assert payload["appName"] == "chatbot"
    assert payload["sessionId"] == "session-1"
    assert payload["newMessage"]["parts"] == [{"text": "Hi"}]
    assert request.call_args_list[-1].args == (
        "DELETE", "/apps/chatbot/users/python-eval/sessions/session-1",
    )


def test_cleanup_after_run_failure():
    with patch("evals.adk_client._request", side_effect=[
        {"id": "session-2"}, RuntimeError("run failed"), None,
    ]) as request:
        with pytest.raises(RuntimeError, match="run failed"):
            ask("conference_agent", "Hi")
    assert request.call_args_list[-1].args[0] == "DELETE"


def test_rejects_unknown_app_before_network_request():
    with patch("evals.adk_client._request") as request:
        with pytest.raises(ValueError):
            ask("../unknown", "Hi")
    request.assert_not_called()


def test_promptfoo_provider_passes_actual_evidence():
    result = {
        "answer": "Bring a laptop.",
        "contexts": ["Bring a laptop."],
        "tool_calls": [{"name": "lookupConference", "args": {"topic": "workshop"}}],
    }
    with patch("evals.promptfoo.provider.ask", return_value=result) as ask_mock:
        response = call_api("What should I bring?", {}, {"vars": {"app": "conference_agent"}})
    ask_mock.assert_called_once_with("conference_agent", "What should I bring?")
    assert response["output"] == result["answer"]
    assert response["metadata"]["contexts"] == result["contexts"]
    context = {"vars": {"expected": "laptop", "topic": "workshop"},
               "metadata": response["metadata"]}
    assert get_assert(response["output"], context)
    assert used_tool(response["output"], context)
    assert used_tool(response["output"], {
        "vars": {"topic": "workshop"}, "providerResponse": response,
    })
    assert not get_assert("No equipment needed", context)
    assert not used_tool(response["output"], {"vars": {"topic": "refund"}})
    assert admits_unknown("I don't know the WiFi password.", {})
    assert not admits_unknown("The WiFi password is secret123.", {})
