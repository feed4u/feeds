"""Tests for llm_client against a fake OpenAI-compatible server.

Run: python3 -m unittest discover -s core/code/base/tests -v
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from fake_llm_server import FakeLLMServer, sequence, static, unused_port_url  # noqa: E402
from llm_client import (  # noqa: E402
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    LLMClient,
    LLMConfig,
    LLMError,
    LLMUnavailable,
    parse_json_reply,
    strip_thinking,
)


def client_for(base_url: str, **overrides) -> LLMClient:
    config = LLMConfig(base_url=base_url, model="fake-model", timeout=5, retries=2, retry_backoff=0)
    for key, value in overrides.items():
        setattr(config, key, value)
    return LLMClient(config, sleep=lambda s: None)


class ConfigTests(unittest.TestCase):
    def test_defaults_point_at_local_lane_with_thinking_off(self):
        config = LLMConfig.from_env({})
        self.assertEqual(config.base_url, DEFAULT_BASE_URL)
        self.assertEqual(DEFAULT_BASE_URL, "http://127.0.0.1:11434/v1")
        self.assertEqual(config.model, DEFAULT_MODEL)
        self.assertEqual(DEFAULT_MODEL, "qwen38-27b-mtp2:latest")
        self.assertIsNone(config.api_key)
        self.assertEqual(config.reasoning_effort, "none")

    def test_openai_when_configured(self):
        config = LLMConfig.from_env({
            "LLM_BASE_URL": "https://api.openai.com/v1/",
            "LLM_MODEL": "gpt-4o-mini",
            "LLM_API_KEY": "sk-test",
        })
        self.assertEqual(config.base_url, "https://api.openai.com/v1")
        self.assertEqual(config.model, "gpt-4o-mini")
        self.assertEqual(config.api_key, "sk-test")
        self.assertIsNone(config.reasoning_effort)  # not sent to remote APIs by default

    def test_openai_key_fallback_and_explicit_empty_effort(self):
        config = LLMConfig.from_env({"OPENAI_API_KEY": "sk-old", "LLM_REASONING_EFFORT": ""})
        self.assertEqual(config.api_key, "sk-old")
        self.assertIsNone(config.reasoning_effort)


class StripThinkingTests(unittest.TestCase):
    def test_strips_think_block(self):
        self.assertEqual(strip_thinking("<think>\nlet me see…\n</think>\n\n{\"a\": 1}"), '{"a": 1}')

    def test_strips_multiple_and_thinking_variant(self):
        text = "<think>x</think>A<thinking>y</thinking>B"
        self.assertEqual(strip_thinking(text), "AB")

    def test_strips_orphan_close_tag(self):
        self.assertEqual(strip_thinking("reasoning here</think>answer"), "answer")

    def test_strips_unclosed_trailing_think(self):
        self.assertEqual(strip_thinking("answer<think>still going"), "answer")

    def test_plain_text_untouched(self):
        self.assertEqual(strip_thinking("  hello  "), "hello")


class ChatTests(unittest.TestCase):
    def test_success_returns_content_and_sends_openai_shape(self):
        with FakeLLMServer(static("hello there")) as server:
            client = client_for(server.base_url, api_key="sk-x", reasoning_effort="none")
            text = client.chat([{"role": "user", "content": "hi"}], max_tokens=50)
        self.assertEqual(text, "hello there")
        body = server.requests[0]
        self.assertEqual(body["model"], "fake-model")
        self.assertEqual(body["messages"], [{"role": "user", "content": "hi"}])
        self.assertEqual(body["max_tokens"], 50)
        self.assertEqual(body["reasoning_effort"], "none")
        self.assertEqual(server.headers[0].get("Authorization"), "Bearer sk-x")

    def test_no_auth_header_without_key(self):
        with FakeLLMServer(static("ok")) as server:
            client_for(server.base_url).chat([{"role": "user", "content": "hi"}])
        self.assertNotIn("Authorization", server.headers[0])

    def test_thinking_stripped_from_reply(self):
        with FakeLLMServer(static("<think>secret chain</think>\n{\"ok\": true}")) as server:
            client = client_for(server.base_url)
            self.assertEqual(client.chat([{"role": "user", "content": "x"}]), '{"ok": true}')
            self.assertEqual(client.chat_json([{"role": "user", "content": "x"}]), {"ok": True})
        self.assertEqual(server.requests[1]["response_format"], {"type": "json_object"})

    def test_timeout_raises_unavailable_after_retries(self):
        with FakeLLMServer(static("late"), delay=1.0) as server:
            client = client_for(server.base_url, timeout=0.2, retries=1)
            started = time.monotonic()
            with self.assertRaises(LLMUnavailable) as ctx:
                client.chat([{"role": "user", "content": "x"}])
            elapsed = time.monotonic() - started
        self.assertIn("timed out", str(ctx.exception))
        self.assertEqual(len(server.requests), 2)  # first try + 1 retry
        self.assertLess(elapsed, 3.0)

    def test_retries_server_error_then_succeeds(self):
        with FakeLLMServer(sequence([(503, "busy"), (200, "fine")])) as server:
            text = client_for(server.base_url).chat([{"role": "user", "content": "x"}])
        self.assertEqual(text, "fine")
        self.assertEqual(len(server.requests), 2)

    def test_client_error_not_retried(self):
        with FakeLLMServer(static("bad model", status=404)) as server:
            with self.assertRaises(LLMError) as ctx:
                client_for(server.base_url).chat([{"role": "user", "content": "x"}])
        self.assertNotIsInstance(ctx.exception, LLMUnavailable)
        self.assertEqual(len(server.requests), 1)

    def test_endpoint_down_gives_clear_error(self):
        client = client_for(unused_port_url())
        with self.assertRaises(LLMUnavailable) as ctx:
            client.check_available(timeout=1)
        self.assertIn("unreachable", str(ctx.exception))
        self.assertIn("LLM_BASE_URL", str(ctx.exception))
        with self.assertRaises(LLMUnavailable):
            client.chat([{"role": "user", "content": "x"}])

    def test_check_available_ok(self):
        with FakeLLMServer(static("x")) as server:
            client_for(server.base_url).check_available()

    def test_empty_reply_is_error(self):
        with FakeLLMServer(static("<think>only thoughts</think>")) as server:
            with self.assertRaises(LLMError):
                client_for(server.base_url).chat([{"role": "user", "content": "x"}])


class ParseJsonTests(unittest.TestCase):
    def test_fenced_and_prose(self):
        self.assertEqual(parse_json_reply('```json\n{"a": [1]}\n```'), {"a": [1]})
        self.assertEqual(parse_json_reply('Sure! {"a": 2} hope that helps'), {"a": 2})

    def test_invalid(self):
        with self.assertRaises(LLMError):
            parse_json_reply("no json here")


if __name__ == "__main__":
    unittest.main()
