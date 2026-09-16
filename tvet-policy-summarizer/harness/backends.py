# LLM backends: Ollama (local), OpenAI-compatible (local or online), Mock (testing without a model).
import json
import os
import re
import urllib.error
import urllib.request
from urllib.parse import urlparse


class BackendError(Exception):
    pass


def _opener_for(url):
    host = (urlparse(url).hostname or "").lower()
    if host in ("localhost", "127.0.0.1", "::1"):
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener()


def _request(url, payload=None, headers=None, timeout=300):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req_headers = {"Content-Type": "application/json"}
    req_headers.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=req_headers, method="POST" if data else "GET")
    try:
        with _opener_for(url).open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise BackendError("HTTP %s from %s: %s" % (exc.code, url, body[:500])) from exc
    except urllib.error.URLError as exc:
        raise BackendError("Cannot reach %s (%s)" % (url, exc.reason)) from exc
    except (TimeoutError, OSError) as exc:
        raise BackendError("Request to %s failed: %s" % (url, exc)) from exc


class OllamaBackend:
    name = "ollama"

    def __init__(self, cfg, model):
        if not model:
            raise ValueError("No model configured for the Ollama backend")
        self.model = model
        self.host = cfg.get("host", "http://127.0.0.1:11434").rstrip("/")
        self.num_ctx = int(cfg.get("num_ctx", 8192))
        self.timeout = int(cfg.get("timeout", 900))
        self.keep_alive = cfg.get("keep_alive", "10m")

    def check(self):
        tags = _request(self.host + "/api/tags", timeout=10)
        names = [m.get("name", "") for m in tags.get("models", [])]
        wanted = self.model if ":" in self.model else self.model + ":latest"
        return wanted in names or self.model in names, names

    def chat(self, messages, json_mode=False, temperature=0.1):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {"temperature": temperature, "num_ctx": self.num_ctx},
        }
        if json_mode:
            payload["format"] = "json"
        data = _request(self.host + "/api/chat", payload, timeout=self.timeout)
        return (data.get("message") or {}).get("content", "")


class OpenAICompatibleBackend:
    name = "openai_compatible"

    def __init__(self, cfg, model):
        if not model:
            raise ValueError("No model configured for the OpenAI-compatible backend")
        self.model = model
        self.base_url = (os.environ.get("TVET_OPENAI_BASE_URL") or cfg.get("base_url", "")).rstrip("/")
        self.api_key = os.environ.get(cfg.get("api_key_env", "OPENAI_API_KEY"), "")
        self.json_mode = bool(cfg.get("json_mode", True))
        self.timeout = int(cfg.get("timeout", 300))
        self.headers = dict(cfg.get("extra_headers") or {})
        if self.api_key:
            self.headers.setdefault("Authorization", "Bearer " + self.api_key)

    def check(self):
        try:
            data = _request(self.base_url + "/models", headers=self.headers, timeout=15)
            names = [m.get("id", "") for m in data.get("data", [])]
            return (self.model in names) if names else True, names
        except BackendError as exc:
            if "HTTP 404" in str(exc):
                return True, []
            raise

    def chat(self, messages, json_mode=False, temperature=0.1):
        payload = {"model": self.model, "messages": messages, "temperature": temperature}
        if json_mode and self.json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = _request(self.base_url + "/chat/completions", payload, headers=self.headers, timeout=self.timeout)
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise BackendError("Unexpected response format: %s" % str(data)[:300]) from exc


class MockBackend:
    # Deterministic fake model for testing the pipeline without Ollama or network access.
    name = "mock"

    def __init__(self, cfg, model):
        self.model = model or "mock"

    def check(self):
        return True, [self.model]

    def chat(self, messages, json_mode=False, temperature=0.1):
        source, is_review = "", False
        for message in messages:
            if message["role"] != "user":
                continue
            match = re.search(r"<(document|summary)>\s*(.*?)\s*</\1>", message["content"], re.S)
            if match:
                source, is_review = match.group(2), match.group(1) == "summary"
                break
        words = re.sub(r"\[Page \d+\]", " ", source).split()
        if not json_mode:
            return "- " + " ".join(words[:40])
        if is_review:
            return json.dumps({"neutral": True, "within_limit": len(words) <= 80, "issues": [],
                               "suggested_revision": ""})
        excerpt = " ".join(w for w in words[:40] if w.isalpha())
        summary = "This mock summary tests the pipeline without a language model. The document text begins: %s." % excerpt
        return json.dumps({
            "title": "Mock record", "issuing_body": "Not stated", "country_or_region": "Not stated",
            "year": "Not stated", "document_type": "Not stated", "summary": summary,
            "keywords": ["mock", "pipeline test", "tvet"],
        })


def get_backend(cfg, agent, backend_override=None, model_override=None):
    name = backend_override or os.environ.get("TVET_BACKEND") or agent.get("backend", "ollama")
    model = model_override or os.environ.get("TVET_MODEL") or agent.get("model")
    backends = cfg.get("backends", {})
    if name == "ollama":
        return OllamaBackend(backends.get("ollama", {}), model)
    if name in ("openai", "openai_compatible"):
        return OpenAICompatibleBackend(backends.get("openai_compatible", {}), model)
    if name == "mock":
        return MockBackend(backends.get("mock", {}), model)
    raise ValueError("Unknown backend '%s' (use ollama, openai_compatible or mock)" % name)
