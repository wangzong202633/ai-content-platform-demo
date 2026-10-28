# -*- coding: utf-8 -*-
"""Real publish providers — plugin architecture.

- WechatMpProvider: official WeChat APIs (works for personal subscription
  accounts): access_token -> upload permanent thumb material -> create draft.
  The article really appears in the MP backend draft box; the operator clicks
  发布 (mass-send APIs need verified accounts, we never fake that).
- WebhookProvider: generic JSON push (企业微信/钉钉/飞书 bots, or a self-built
  relay for any platform with an API).
- Platforms without public content APIs (xhs/douyin/channels) stay on the
  copy-and-publish content package path — see design doc §9.
"""
import json
import time

import httpx

WX_BASE = "https://api.weixin.qq.com/cgi-bin"


class PublishError(Exception):
    """Friendly, operator-actionable publish failure."""


# ── access_token cache (per appid, 7200s validity, refresh 5min early) ──
_token_cache: dict[str, tuple[str, float]] = {}


def _wx_token(appid: str, secret: str, force: bool = False) -> str:
    hit = _token_cache.get(appid)
    if not force and hit and hit[1] > time.time():
        return hit[0]
    r = httpx.get(f"{WX_BASE}/token", params={
        "grant_type": "client_credential", "appid": appid, "secret": secret}, timeout=20)
    d = r.json()
    if "access_token" not in d:
        code, msg = d.get("errcode"), d.get("errmsg", "")
        if code == 40164:
            raise PublishError(
                f"invalid ip：请在公众号后台「设置与开发-基本配置-IP白名单」中"
                f"添加本机公网 IP 后重试（微信返回：{msg}）")
        if code in (40001, 41004, 40125):
            raise PublishError("AppSecret 校验失败，请核对 AppID/AppSecret（微信返回：%s）" % msg)
        if code == 40013:
            raise PublishError("AppID 无效，请核对（微信返回：%s）" % msg)
        raise PublishError(f"获取 access_token 失败（errcode={code}：{msg}）")
    token = d["access_token"]
    _token_cache[appid] = (token, time.time() + d.get("expires_in", 7200) - 300)
    return token


def wx_connect_check(appid: str, secret: str) -> str:
    """Verify credentials by fetching a token. Returns a human message."""
    _wx_token(appid, secret, force=True)
    return "access_token 获取成功，公众号已连接"


def _wx_upload_thumb(token: str, image_path: str) -> str:
    with open(image_path, "rb") as f:
        r = httpx.post(f"{WX_BASE}/material/add_material",
                       params={"access_token": token, "type": "image"},
                       files={"media": ("cover.png", f, "image/png")}, timeout=60)
    d = r.json()
    if "media_id" not in d:
        raise PublishError(f"封面上传失败（errcode={d.get('errcode')}：{d.get('errmsg')}）")
    return d["media_id"]


def _html(copy_text: str, account_name: str) -> str:
    paras = [p for p in copy_text.split("\n") if p.strip()]
    body = "".join(f"<p style=\"line-height:1.9\">{p}</p>" for p in paras)
    return (f"{body}<p style=\"color:#888;font-size:13px\">—— 由 AI 内容平台"
            f"发布至「{account_name}」</p>")


def wx_publish_draft(appid: str, secret: str, title: str, copy_text: str,
                     cover_path: str, account_name: str) -> dict:
    """Create a real draft in the WeChat MP backend. Returns draft info."""
    title = (title or "未命名内容")[:64]
    token = _wx_token(appid, secret)
    thumb_media_id = _wx_upload_thumb(token, cover_path)
    digest = copy_text.replace("\n", " ")[:54]
    r = httpx.post(f"{WX_BASE}/draft/add", params={"access_token": token}, json={
        "articles": [{
            "title": title, "author": account_name, "digest": digest,
            "content": _html(copy_text, account_name),
            "thumb_media_id": thumb_media_id,
            "need_open_comment": 0, "only_fans_can_comment": 0,
        }]}, timeout=30)
    d = r.json()
    if "media_id" not in d:
        if d.get("errcode") == 48001:
            raise PublishError(
                "该公众号无草稿箱权限（未认证订阅号请到公众号后台确认「新的草稿箱能力」已开启）")
        raise PublishError(f"创建草稿失败（errcode={d.get('errcode')}：{d.get('errmsg')}）")
    return {"draft_media_id": d["media_id"],
            "backend": "https://mp.weixin.qq.com（草稿箱 → 图文素材）"}


# ── generic webhook ────────────────────────────────────────────────
def webhook_send(url: str, payload: dict) -> dict:
    r = httpx.post(url, json=payload, timeout=20)
    ok = 200 <= r.status_code < 300
    if not ok:
        raise PublishError(f"Webhook 投递失败（HTTP {r.status_code}：{r.text[:120]}）")
    return {"delivered": True, "status_code": r.status_code}


def build_payload(package: dict, content_title: str) -> dict:
    return {
        "source": "ai-content-platform-demo",
        "account": package.get("account_name", ""),
        "platform": package.get("platform", ""),
        "title": content_title,
        "copy": package.get("copy_text", ""),
        "cover_url": package.get("image_url", ""),
        "tags": json.loads(package.get("tags_json") or "[]"),
        "suggest_time": package.get("suggest_time", ""),
        "published_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
