"""Provider-neutral client for OpenAI-compatible chat completion endpoints.

Talks to any server that implements ``POST {base_url}/chat/completions``:
the local Ollama lanes on this host, OpenAI itself, or anything similar.
Uses only the standard library so the pipeline needs no SDK.

Configuration (environment, all optional):
    LLM_BASE_URL          default http://127.0.0.1:11434/v1 (local ollama-gpu0 lane)
    LLM_MODEL             default qwen38-27b-mtp2:latest
    LLM_API_KEY           sent as a Bearer token when set (falls back to OPENAI_API_KEY)
    LLM_TIMEOUT           seconds per request, default 600
    LLM_RETRIES           extra attempts after a failure, default 2
    LLM_REASONING_EFFORT  passed as ``reasoning_effort``; defaults to "none" for
                          local endpoints (turns Qwen thinking off), unset otherwise.
                          Set to "" to never send it.

To use OpenAI: LLM_BASE_URL=https://api.openai.com/v1 LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-...
"""

from __future__ import annotations

import json
import os
import re
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

DEFAULT_BASE_URL = "http://127.0.0.1:11434/v1"
DEFAULT_MODEL = "qwen38-27b-mtp2:latest"

_THINK_RE = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.DOTALL | re.IGNORECASE)
_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}


class LLMError(RuntimeError):
    """The endpoint answered, but not with a usable completion."""


class LLMUnavailable(LLMError):
    """The endpoint could not be reached (down, refused, timed out)."""


def strip_thinking(text: str) -> str:
    """Remove Qwen-style ``<think>…</think>`` blocks (and an unclosed trailing one)."""
    text = _THINK_RE.sub("", text or "")
    # A reply cut off mid-thought leaves an opening tag with no close.
    text = re.split(r"<think(?:ing)?>", text, flags=re.IGNORECASE)[0]
    # Some templates emit only the closing tag (the opening one is in the prompt).
    if re.search(r"</think(?:ing)?>", text, flags=re.IGNORECASE):
        text = re.split(r"</think(?:ing)?>", text, flags=re.IGNORECASE)[-1]
    return text.strip()


def _is_local(base_url: str) -> bool:
    return (urlparse(base_url).hostname or "") in _LOCAL_HOSTS


@dataclass
class LLMConfig:
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    api_key: Optional[str] = None
    timeout: float = 600.0
    retries: int = 2
    retry_backoff: float = 5.0
    reasoning_effort: Optional[str] = None

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> "LLMConfig":
        env = os.environ if env is None else env
        base_url = (env.get("LLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        if "LLM_REASONING_EFFORT" in env:
            effort = env["LLM_REASONING_EFFORT"] or None
        else:
            effort = "none" if _is_local(base_url) else None
        return cls(
            base_url=base_url,
            model=env.get("LLM_MODEL") or DEFAULT_MODEL,
            api_key=env.get("LLM_API_KEY") or env.get("OPENAI_API_KEY") or None,
            timeout=float(env.get("LLM_TIMEOUT") or 600),
            retries=int(env.get("LLM_RETRIES") or 2),
            reasoning_effort=effort,
        )


@dataclass
class LLMClient:
    config: LLMConfig = field(default_factory=LLMConfig.from_env)
    sleep: Callable[[float], None] = time.sleep
    # Running totals of the ``usage`` the endpoint reports (prompt/completion tokens).
    usage: Dict[str, int] = field(default_factory=dict)

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _request(self, method: str, path: str, body: Optional[dict], timeout: float) -> Any:
        url = f"{self.config.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers=self._headers())
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def check_available(self, timeout: float = 10.0) -> None:
        """Raise LLMUnavailable unless the endpoint answers ``GET /models``."""
        try:
            self._request("GET", "/models", None, timeout)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise LLMUnavailable(
                    f"LLM endpoint {self.config.base_url} rejected the credentials "
                    f"(HTTP {exc.code}); set LLM_API_KEY"
                ) from exc
            if exc.code >= 500:
                raise LLMUnavailable(
                    f"LLM endpoint {self.config.base_url} is failing (HTTP {exc.code})"
                ) from exc
            # Some compatible servers do not implement /models; reachable is enough.
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as exc:
            raise LLMUnavailable(
                f"LLM endpoint {self.config.base_url} is unreachable: {exc}. "
                "Start the lane or point LLM_BASE_URL at a running OpenAI-compatible server."
            ) from exc

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        max_tokens: int = 2000,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> str:
        """Return the assistant text for ``messages`` with thinking stripped.

        Retries timeouts, connection errors, HTTP 429 and 5xx with backoff.
        Raises LLMUnavailable when every attempt failed to reach the server and
        LLMError for any other unusable answer.
        """
        body: Dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if self.config.reasoning_effort:
            body["reasoning_effort"] = self.config.reasoning_effort
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        attempts = self.config.retries + 1
        last_exc: Optional[Exception] = None
        for attempt in range(1, attempts + 1):
            try:
                payload = self._request("POST", "/chat/completions", body, self.config.timeout)
                break
            except urllib.error.HTTPError as exc:
                detail = exc.read()[:500].decode("utf-8", "replace") if exc.fp else ""
                if exc.code == 429 or exc.code >= 500:
                    last_exc = LLMUnavailable(
                        f"LLM endpoint {self.config.base_url} returned HTTP {exc.code}: {detail}"
                    )
                else:
                    raise LLMError(
                        f"LLM endpoint {self.config.base_url} returned HTTP {exc.code}: {detail}"
                    ) from exc
            except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as exc:
                last_exc = LLMUnavailable(
                    f"LLM endpoint {self.config.base_url} unreachable or timed out "
                    f"after {self.config.timeout:.0f}s: {exc}"
                )
            except json.JSONDecodeError as exc:
                raise LLMError(f"LLM endpoint returned non-JSON: {exc}") from exc
            if attempt < attempts:
                self.sleep(self.config.retry_backoff * attempt)
        else:
            assert last_exc is not None
            raise last_exc

        reported = payload.get("usage") if isinstance(payload, dict) else None
        if isinstance(reported, dict):
            for key in ("prompt_tokens", "completion_tokens"):
                if isinstance(reported.get(key), int):
                    self.usage[key] = self.usage.get(key, 0) + reported[key]

        try:
            content = payload["choices"][0]["message"].get("content") or ""
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise LLMError(f"Unexpected completion shape: {str(payload)[:300]}") from exc
        text = strip_thinking(content)
        if not text:
            raise LLMError("LLM returned an empty completion")
        return text

    def chat_json(self, messages: List[Dict[str, str]], **kwargs: Any) -> Any:
        """Like ``chat`` but parse the answer as JSON (tolerating code fences)."""
        text = self.chat(messages, json_mode=True, **kwargs)
        return parse_json_reply(text)


def parse_json_reply(text: str) -> Any:
    """Parse JSON from a model reply, tolerating ```json fences and stray prose."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = min((i for i in (cleaned.find("{"), cleaned.find("[")) if i >= 0), default=-1)
        end = max(cleaned.rfind("}"), cleaned.rfind("]"))
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass
    raise LLMError(f"LLM reply is not valid JSON: {text[:300]}")


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MODEL",
    "LLMClient",
    "LLMConfig",
    "LLMError",
    "LLMUnavailable",
    "parse_json_reply",
    "strip_thinking",
]
