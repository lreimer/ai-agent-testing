"""Minimal client for the Java ADK development server's non-streaming API."""

import json
import os
from urllib.parse import quote
from urllib.request import Request, urlopen


def _request(method, path, payload=None):
    base = os.environ.get("ADK_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(
        base + path, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=120) as response:
        body = response.read()
        return json.loads(body) if body else None


def parse_events(events):
    """Extract the final answer and actual tool evidence, not expected fixtures."""
    answer = ""
    tool_calls = []
    contexts = []
    for event in events:
        if event.get("errorMessage") or event.get("errorCode"):
            raise RuntimeError(f"ADK run failed: {event.get('errorMessage') or event['errorCode']}")
        parts = (event.get("content") or {}).get("parts", [])
        texts = []
        has_tool = False
        for part in parts:
            if part.get("functionCall"):
                has_tool = True
                tool_calls.append(part["functionCall"])
            if part.get("functionResponse"):
                has_tool = True
                result = part["functionResponse"].get("response", {})
                contexts.extend(result.get("contexts", []))
            if part.get("text") and not part.get("thought"):
                texts.append(part["text"])
        if texts and not has_tool and event.get("content", {}).get("role") == "model":
            answer = "".join(texts)
    if not answer.strip():
        raise RuntimeError("ADK returned no final text response")
    return {"answer": answer, "tool_calls": tool_calls, "contexts": contexts}


def ask(app, prompt):
    if app not in {"chatbot", "conference_agent"}:
        raise ValueError(f"Unknown demo app: {app}")
    path = f"/apps/{app}/users/python-eval/sessions"
    session = _request("POST", path, {"state": {}})
    session_path = f"{path}/{quote(session['id'], safe='')}"
    try:
        events = _request("POST", "/run", {
            "appName": app,
            "userId": "python-eval",
            "sessionId": session["id"],
            "newMessage": {"role": "user", "parts": [{"text": prompt}]},
            "streaming": False,
        })
        return parse_events(events)
    finally:
        _request("DELETE", session_path)
