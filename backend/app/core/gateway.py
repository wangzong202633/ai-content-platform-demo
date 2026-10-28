# -*- coding: utf-8 -*-
"""AI capability gateway — dual-provider registry for text & image models.

Provider selection: first provider WITH a configured key wins (.env), or the
explicit TEXT_PROVIDER / IMAGE_PROVIDER override. Without any key we stay in
offline/template mode — badges in the UI report the live tier honestly.
"""
import os
import time

import httpx

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())


_load_env()

OFFLINE = os.environ.get("DEMO_OFFLINE", "1") not in ("0", "false", "False")

# ── provider registry ──────────────────────────────────────────────
# zhipu: text glm-4-flash is free-tier; image cogview-4 ~¥0.06/张
# ark (volcano): text doubao / image seedream — key validated, waiting for
# the client to enable models in the console.
PROVIDERS = {
    "zhipu": {
        "base": "https://open.bigmodel.cn/api/paas/v4",
        "key": os.environ.get("ZHIPU_API_KEY", ""),
        "text_model": os.environ.get("ZHIPU_TEXT_MODEL", "glm-4-flash"),
        "image_model": os.environ.get("ZHIPU_IMAGE_MODEL", "cogview-4"),
    },
    "ark": {
        "base": "https://ark.cn-beijing.volces.com/api/v3",
        "key": os.environ.get("ARK_API_KEY", os.environ.get("LLM_API_KEY", "")),
        "text_model": os.environ.get("ARK_TEXT_MODEL", os.environ.get("LLM_MODEL", "")),
        "image_model": os.environ.get("ARK_IMAGE_MODEL", "doubao-seedream-4-0-250828"),
    },
}


def _pick(kind: str):
    """Return (provider_name, cfg) for the first provider with a usable key."""
    explicit = os.environ.get(f"{kind.upper()}_PROVIDER", "").lower()
    names = [explicit] if explicit and explicit in PROVIDERS else list(PROVIDERS)
    for name in names:
        cfg = PROVIDERS[name]
        if cfg["key"] and cfg.get(f"{kind}_model"):
            return name, cfg
    return None, None


def text_status() -> dict:
    name, cfg = _pick("text")
    return {"provider": name or "none", "model": cfg[f"text_model"] if cfg else "scripted",
            "live": bool(name) and not OFFLINE}


def image_status() -> dict:
    name, cfg = _pick("image")
    return {"provider": name or "none", "model": cfg[f"image_model"] if cfg else "template",
            "live": bool(name) and not OFFLINE}


# ── text chat (OpenAI-compatible, both providers) ─────────────────
# with a light hash cache: identical prompt+temperature replays the warmed
# answer — the same lifeline llm.py gives content generation.
import hashlib

_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "cache")
os.makedirs(_CACHE_DIR, exist_ok=True)


def chat(prompt: str, temperature: float = 0.7, timeout: float = 90) -> str:
    name, cfg = _pick("text")
    if not name or OFFLINE:
        raise RuntimeError("no live text provider")
    key = hashlib.sha256(f"chat@@{temperature}@@{prompt}".encode("utf-8")).hexdigest()
    cache_path = os.path.join(_CACHE_DIR, f"{key}.json")
    if os.path.exists(cache_path):
        import json as _json
        with open(cache_path, encoding="utf-8") as f:
            obj = _json.load(f)
        if isinstance(obj, dict) and "text" in obj:
            return obj["text"]
    resp = httpx.post(
        f"{cfg['base']}/chat/completions",
        headers={"Authorization": f"Bearer {cfg['key']}"},
        json={"model": cfg["text_model"], "temperature": temperature,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=timeout,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    try:
        import json as _json
        with open(cache_path, "w", encoding="utf-8") as f:
            _json.dump({"text": text}, f, ensure_ascii=False)
    except OSError:
        pass
    return text


# ── image generation (zhipu cogview / ark seedream, same REST shape) ──
# CogView-4 exact sizes; Seedream takes 1K/2K/4K buckets — the compositor
# crops to the exact channel spec anyway, so the bg never needs exact pixels.
SUPPORTED_SIZES = {"1024x1024", "768x1344", "864x1152", "1344x768",
                   "1152x864", "1440x720", "720x1440"}


def _image_request_size(provider: str, size: str) -> str:
    if provider == "zhipu":
        return size if size in SUPPORTED_SIZES else "1440x720"
    # ark / seedream: bucket by resolution
    return size if size in {"1K", "2K", "4K"} else "2K"


def generate_image(prompt: str, size: str = "1440x720", timeout: float = 120):
    """Returns (image_bytes, provider_name, latency_ms). Raises on failure.
    Warm-cache aware: identical prompt+size replays the stored PNG (demo
    lifeline — a live Seedream 2K call takes ~50s and must not block a demo
    when the network flakes)."""
    name, cfg = _pick("image")
    if not name or OFFLINE:
        raise RuntimeError("no live image provider")
    req_size = _image_request_size(name, size)
    key = hashlib.sha256(f"img@@{cfg['image_model']}@@{req_size}@@{prompt}".encode("utf-8")).hexdigest()
    cache_path = os.path.join(_CACHE_DIR, f"{key}.png")
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            return f.read(), name, 0
    started = time.time()
    resp = httpx.post(
        f"{cfg['base']}/images/generations",
        headers={"Authorization": f"Bearer {cfg['key']}"},
        json={"model": cfg["image_model"], "prompt": prompt, "size": req_size,
              "response_format": "url", "watermark": False, "stream": False},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()["data"][0]
    url = data.get("url")
    if url:
        img = httpx.get(url, timeout=60)
        img.raise_for_status()
        content = img.content
    elif data.get("b64_json"):
        import base64
        content = base64.b64decode(data["b64_json"])
    else:
        raise RuntimeError("provider returned no image")
    try:
        with open(cache_path, "wb") as f:
            f.write(content)
    except OSError:
        pass
    return content, name, int((time.time() - started) * 1000)
