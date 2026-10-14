"""A tiny OpenAI-compatible HTTP server for tests (stdlib only)."""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Dict, List, Optional

# responder(request_body) -> (status, reply_content_or_body)
Responder = Callable[[dict], "tuple[int, object]"]


class FakeLLMServer:
    def __init__(self, responder: Responder, delay: float = 0.0):
        self.responder = responder
        self.delay = delay
        self.requests: List[dict] = []
        self.headers: List[Dict[str, str]] = []
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # keep test output clean
                pass

            def _send(self, status: int, payload: object) -> None:
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                if self.path.endswith("/models"):
                    self._send(200, {"object": "list", "data": [{"id": "fake-model"}]})
                else:
                    self._send(404, {"error": "not found"})

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                server.requests.append(body)
                server.headers.append(dict(self.headers))
                if server.delay:
                    time.sleep(server.delay)
                status, reply = server.responder(body)
                if status != 200:
                    self._send(status, {"error": {"message": str(reply)}})
                    return
                content = reply if isinstance(reply, str) else json.dumps(reply)
                self._send(200, {
                    "id": "chatcmpl-test",
                    "object": "chat.completion",
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                                 "finish_reason": "stop"}],
                })

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}/v1"

    def __enter__(self) -> "FakeLLMServer":
        self.thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


def unused_port_url() -> str:
    """A base URL on a port nothing listens on (connection refused)."""
    import socket

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return f"http://127.0.0.1:{port}/v1"


def static(content: object, status: int = 200) -> Responder:
    return lambda body: (status, content)


def sequence(replies: List["tuple[int, object]"]) -> Responder:
    state = {"i": 0}

    def respond(body: dict):
        reply = replies[min(state["i"], len(replies) - 1)]
        state["i"] += 1
        return reply

    return respond


__all__ = ["FakeLLMServer", "static", "sequence", "unused_port_url", "Optional"]
