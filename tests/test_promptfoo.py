"""Exercise the real CLI/Python integration without a paid model."""

import json
import os
from pathlib import Path
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "node_modules" / ".bin" / "promptfoo"


@pytest.mark.skipif(not CLI.exists(), reason="Run npm ci to install the PromptFoo CLI")
def test_promptfoo_python_wiring(tmp_path):
    deleted_sessions = []

    class FixtureAPI(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, value):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(value).encode())

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path.endswith("/sessions"):
                self.respond({"id": "fixture-session"})
                return
            question = payload["newMessage"]["parts"][0]["text"]
            answer = "The keynote starts at 09:00 in Hall A."
            events = []
            if "workshop" in question:
                answer = "The AI testing workshop starts at 14:00 in Room B. Bring a laptop."
                events = [
                    {"content": {"role": "model", "parts": [{"functionCall": {
                        "name": "lookupConference", "args": {"topic": "workshop"},
                    }}]}},
                    {"content": {"role": "user", "parts": [{"functionResponse": {
                        "name": "lookupConference", "response": {"contexts": [answer]},
                    }}]}},
                ]
            elif "WiFi" in question:
                answer = "I do not know the WiFi password."
            self.respond(events + [{"content": {"role": "model", "parts": [{"text": answer}]}}])

        def do_DELETE(self):
            deleted_sessions.append(self.path)
            self.respond(None)

    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureAPI)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = subprocess.run(
            [str(CLI), "eval", "-c", str(ROOT / "evals/promptfoo/promptfooconfig.yaml"),
             "--no-cache", "--no-write", "--no-progress-bar"],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
            env={
                **os.environ,
                "ADK_BASE_URL": f"http://127.0.0.1:{server.server_port}",
                "PYTHONPATH": str(ROOT),
                "PROMPTFOO_PYTHON": sys.executable,
                "PROMPTFOO_CONFIG_DIR": str(tmp_path),
                "PROMPTFOO_DISABLE_TELEMETRY": "1",
            },
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert len(deleted_sessions) == 4
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
