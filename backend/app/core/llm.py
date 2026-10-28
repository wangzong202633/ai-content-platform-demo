# -*- coding: utf-8 -*-
"""LLM client with the three-tier demo lifeline: cache -> real API -> scripted.

- cache/:  pre-baked JSON per sha256(task+prompt). Runs offline forever.
- real API: OpenAI-compatible endpoint via .env (LLM_API_BASE/LLM_API_KEY/LLM_MODEL).
- scripted fallback: app.core.scripted (deterministic, high quality).

`mode` is reported on every call so the UI/health endpoint can show which
tier served the request — the observability principle, demo edition.
"""
import json
import os
import time

import httpx

from . import scripted

_HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.abspath(os.path.join(_HERE, "..", "..", "cache"))
os.makedirs(CACHE_DIR, exist_ok=True)


def _load_env():
    env_path = os.path.join(os.path.dirname(CACHE_DIR), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())


_load_env()

# Single source of truth for provider selection lives in gateway.py
# (ark/doubao first, zhipu backup). Content generation goes live through the
# same channel the moment a text model is enabled + DEMO_OFFLINE=0.
from . import gateway  # noqa: E402

_gw = gateway._pick("text")
_gw_cfg = _gw[1] or {}
API_BASE = (_gw_cfg.get("base") or "").rstrip("/")
API_KEY = _gw_cfg.get("key") or ""
MODEL = _gw_cfg.get("text_model") or "demo-scripted"
OFFLINE = gateway.OFFLINE

_stats = {"cache_hits": 0, "api_calls": 0, "scripted_served": 0}


def _cache_path(key: str) -> str:
    return os.path.join(CACHE_DIR, f"{key}.json")


def _cache_get(key: str):
    p = _cache_path(key)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            _stats["cache_hits"] += 1
            return json.load(f)
    return None


def _cache_put(key: str, obj) -> None:
    with open(_cache_path(key), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def _api_chat(prompt: str):
    """Single non-streaming chat call, strict JSON expected."""
    resp = httpx.post(
        f"{API_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"model": MODEL,
              "temperature": 0,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=90,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    # extract first JSON object from the reply
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON in model reply")
    return json.loads(text[start:end + 1])


def complete(task: str, prompt: str, scripted_obj):
    """Returns (obj, mode). mode in {cache, api, scripted}."""
    key = scripted.key_of(task, prompt)
    cached = _cache_get(key)
    if cached is not None:
        return cached, "cache"
    if not OFFLINE and API_BASE and API_KEY:
        try:
            _stats["api_calls"] += 1
            obj = _api_chat(prompt)
            _cache_put(key, obj)
            return obj, "api"
        except Exception:
            pass  # fall through to scripted — the show must go on
    _stats["scripted_served"] += 1
    return scripted_obj, "scripted"


def stream_tokens(text: str, chunk: int = 3, delay: float = 0.014):
    """Yield text chunks with typing rhythm (used inside SSE generators)."""
    for i in range(0, len(text), chunk):
        yield text[i:i + chunk]
        time.sleep(delay)


def stats() -> dict:
    from . import gateway as _gw
    ts = _gw.text_status()
    return {
        "model": (ts["model"] if ts["live"] else MODEL),
        "mode": ("live-api" if ts["live"] else "offline"),
        "text_provider": ts["provider"],
        "api_base_configured": bool(API_BASE),
        **_stats,
    }
