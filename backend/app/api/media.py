# -*- coding: utf-8 -*-
"""Personal self-media matrix + AI image generation APIs (design doc §4/§5)."""
import json
import os
import time
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .. import db
from ..core import compose, gateway, persona, publish

router = APIRouter()


# ── accounts ───────────────────────────────────────────────────────
class AccountReq(BaseModel):
    name: str
    platform: str
    persona: str
    persona_key: str = "engineer"
    followers: int = 0
    owner: str = ""


@router.get("/api/accounts")
def list_accounts():
    rows = db.query("SELECT * FROM accounts ORDER BY id")
    for r in rows:
        r["platform_label"] = persona.PLATFORM_LABELS.get(r["platform"], r["platform"])
        r["packages"] = db.query_one(
            "SELECT COUNT(*) AS n FROM content_packages WHERE account_id=?", (r["id"],))["n"]
        r["published"] = db.query_one(
            "SELECT COUNT(*) AS n FROM content_packages WHERE account_id=? AND status='published'",
            (r["id"],))["n"]
    return rows


@router.post("/api/accounts")
def create_account(req: AccountReq):
    aid = db.execute(
        "INSERT INTO accounts(name,platform,persona,persona_key,followers,owner,auth_status) "
        "VALUES(?,?,?,?,?,?,?)",
        (req.name, req.platform, req.persona, req.persona_key, req.followers,
         req.owner or req.name, "authorized"))
    return db.query_one("SELECT * FROM accounts WHERE id=?", (aid,))


# ── image generation (three tiers: api -> template) ────────────────
class ImageReq(BaseModel):
    prompt: str = ""
    size: str = "1440x720"          # AI background size
    spec: dict | None = None        # target poster spec {label,w,h}
    title: str = ""
    subtitle: str = ""
    cta: str = ""
    design_hint: dict | None = None
    compose: bool = True


@router.post("/api/images/generate")
def generate_image(req: ImageReq):
    """Returns {url, mode, provider, latency_ms, composed}. mode: live|template."""
    if not req.prompt and not req.spec:
        raise HTTPException(400, "prompt 或 spec 至少一项")
    dh = req.design_hint or {}
    started = time.time()
    mode, provider, latency = "template", "template-synthesis", 0
    bg = None
    prompt = req.prompt or persona.image_prompt(dh, (req.spec or {}).get("label", "封面"))
    if gateway.image_status().get("live"):
        try:
            content, provider, latency = gateway.generate_image(prompt, req.size)
            import io
            from PIL import Image
            bg = Image.open(io.BytesIO(content))
            mode = "live"
        except Exception:
            bg = None  # fall through to template
    if bg is None:
        spec = req.spec or {"w": 1440, "h": 720}
        bg = compose.template_background(spec["w"], spec["h"], dh)
        latency = int((time.time() - started) * 1000)

    name = f"img_{uuid.uuid4().hex[:10]}.png"
    if req.compose and req.spec:
        path = compose.compose_poster(
            bg, req.spec, req.title or "未命名标题",
            req.subtitle or "", req.cta or "", dh,
            req.spec.get("label", "封面"), name)
    else:
        path = os.path.join(compose.MEDIA_DIR, name)
        bg.save(path, "PNG")
    return {"url": f"/media/{name}", "mode": mode, "provider": provider,
            "latency_ms": latency, "prompt": prompt}


@router.get("/media/{name}")
def media_file(name: str):
    path = os.path.join(compose.MEDIA_DIR, os.path.basename(name))
    if not os.path.exists(path):
        raise HTTPException(404, "文件不存在")
    return FileResponse(path)


# ── content packages ───────────────────────────────────────────────
class PackageReq(BaseModel):
    account_ids: list[int]


@router.post("/api/contents/{cid}/package")
def build_package(cid: int, req: PackageReq):
    """For each account: persona-rewritten copy + platform-spec cover
    (one shared AI/template background, programmatic text per platform)."""
    row = db.query_one("SELECT * FROM contents WHERE id=?", (cid,))
    if not row:
        raise HTTPException(404, f"内容 #{cid} 不存在")
    body = json.loads(row["body_json"] or "{}")
    dh = body.get("design_hint", {})

    accounts = []
    for aid in req.account_ids:
        a = db.query_one("SELECT * FROM accounts WHERE id=?", (aid,))
        if a:
            accounts.append(a)
    if not accounts:
        raise HTTPException(400, "未选择账号")

    # 1) one shared background (AI if key configured, template otherwise)
    img_mode = "template"
    bg = None
    if gateway.image_status().get("live"):
        try:
            spec0 = persona.PACKAGE_SPECS.get(accounts[0]["platform"])
            content, provider, _ = gateway.generate_image(
                persona.image_prompt(dh, "封面"), compose.BG_SIZES.get(
                    (spec0["w"], spec0["h"]), "1440x720") if spec0 else "1440x720")
            import io
            from PIL import Image
            bg = Image.open(io.BytesIO(content))
            img_mode = "live"
        except Exception:
            bg = None

    items = []
    for acc in accounts:
        spec = persona.PACKAGE_SPECS.get(acc["platform"])
        if not spec:
            continue
        result, copy_mode = persona.persona_rewrite(acc, body)
        bg_img = bg if bg is not None else compose.template_background(
            spec["w"], spec["h"], dh)
        fname = f"pkg_{cid}_{acc['id']}_{uuid.uuid4().hex[:6]}.png"
        compose.compose_poster(bg_img, spec, body.get("title", row["title"]),
                               result["copy"][:40].replace("\n", " "), "查看全文", dh,
                               spec["label"], fname)
        pid = db.execute(
            "INSERT INTO content_packages(content_id,account_id,copy_text,image_url,"
            "tags_json,suggest_time,status) VALUES(?,?,?,?,?,?,?)",
            (cid, acc["id"], result["copy"], f"/media/{fname}",
             json.dumps(result["tags"], ensure_ascii=False), result["suggest_time"], "draft"))
        db.execute("INSERT INTO events(name,payload_json) VALUES('content_package',?)",
                   (json.dumps({"content_id": cid, "account_id": acc["id"],
                                "platform": acc["platform"], "copy_mode": copy_mode},
                               ensure_ascii=False),))
        items.append({"package_id": pid, "account": {k: acc[k] for k in
                                                     ("id", "name", "platform", "persona")},
                      "platform_label": persona.PLATFORM_LABELS.get(acc["platform"], acc["platform"]),
                      "copy": result["copy"], "copy_mode": copy_mode,
                      "tags": result["tags"], "suggest_time": result["suggest_time"],
                      "cover_url": f"/media/{fname}", "spec": spec["size"],
                      "status": "draft"})

    return {"content_id": cid, "image_mode": img_mode, "items": items}


class ReceiptReq(BaseModel):
    link: str = ""
    note: str = ""
    reach: int = 0


@router.post("/api/packages/{pid}/receipt")
def receipt(pid: int, req: ReceiptReq):
    row = db.query_one("SELECT * FROM content_packages WHERE id=?", (pid,))
    if not row:
        raise HTTPException(404, "内容包不存在")
    db.execute("UPDATE content_packages SET status='published' WHERE id=?", (pid,))
    db.execute(
        "INSERT INTO publish_receipts(package_id,link,note,reach) VALUES(?,?,?,?)",
        (pid, req.link, req.note, req.reach))
    db.execute("INSERT INTO events(name,payload_json) VALUES('content_distribute',?)",
               (json.dumps({"package_id": pid, "channel": "personal_media",
                            "link": req.link[:80]}, ensure_ascii=False),))
    return {"ok": True}


@router.get("/api/contents/{cid}/packages")
def list_packages(cid: int):
    rows = db.query(
        "SELECT p.*, a.name AS account_name, a.platform, a.auth_status FROM content_packages p "
        "JOIN accounts a ON a.id=p.account_id WHERE p.content_id=? ORDER BY p.id DESC", (cid,))
    for r in rows:
        r["platform_label"] = persona.PLATFORM_LABELS.get(r["platform"], r["platform"])
        try:
            r["tags"] = json.loads(r.pop("tags_json") or "[]")
        except Exception:
            r["tags"] = []
    return rows


# ── real account connection + publish (plugin providers) ───────────
class ConnectReq(BaseModel):
    appid: str = ""
    secret: str = ""
    webhook_url: str = ""


@router.post("/api/accounts/{aid}/connect")
def connect_account(aid: int, req: ConnectReq):
    """Verify credentials against the real platform, then store them."""
    acc = db.query_one("SELECT * FROM accounts WHERE id=?", (aid,))
    if not acc:
        raise HTTPException(404, "账号不存在")
    config, verify_msg = {}, ""
    if req.appid and req.secret:
        if acc["platform"] not in ("wechat_mp_personal", "wechat_mp"):
            raise HTTPException(400, "该平台不支持公众号凭据接入")
        try:
            verify_msg = publish.wx_connect_check(req.appid.strip(), req.secret.strip())
            config = {"appid": req.appid.strip(), "secret": req.secret.strip(),
                      "channel": "wechat_draft"}
        except publish.PublishError as e:
            raise HTTPException(409, str(e))
    elif req.webhook_url:
        config = {"webhook_url": req.webhook_url.strip(), "channel": "webhook"}
        verify_msg = "Webhook 通道已配置（发布时投递验证）"
    else:
        raise HTTPException(400, "请填写公众号 AppID/AppSecret 或 Webhook 地址")
    db.execute("UPDATE accounts SET auth_status='connected', config_json=? WHERE id=?",
               (json.dumps(config, ensure_ascii=False), aid))
    db.execute("INSERT INTO events(name,payload_json) VALUES('account_connect',?)",
               (json.dumps({"account_id": aid, "channel": config["channel"]},
                           ensure_ascii=False),))
    row = db.query_one("SELECT * FROM accounts WHERE id=?", (aid,))
    row["config_json"] = "***"  # never echo secrets back
    return {"account": row, "message": verify_msg}


@router.post("/api/accounts/{aid}/disconnect")
def disconnect_account(aid: int):
    db.execute("UPDATE accounts SET auth_status='authorized', config_json='{}' WHERE id=?", (aid,))
    return {"ok": True}


@router.post("/api/packages/{pid}/publish")
def publish_package(pid: int):
    """Real publish via the account's connected channel.
    - wechat_draft: creates an actual draft in the MP backend (official API)
    - webhook: delivers the content package payload to the configured URL
    """
    pkg = db.query_one(
        "SELECT p.*, a.name AS account_name, a.platform, a.auth_status, a.config_json "
        "FROM content_packages p JOIN accounts a ON a.id=p.account_id WHERE p.id=?", (pid,))
    if not pkg:
        raise HTTPException(404, "内容包不存在")
    if pkg["auth_status"] != "connected":
        raise HTTPException(409, "该账号未接入真实通道（公众号凭据或 Webhook）")
    config = json.loads(pkg["config_json"] or "{}")
    channel = config.get("channel")
    content = db.query_one("SELECT title FROM contents WHERE id=?", (pkg["content_id"],))

    try:
        if channel == "wechat_draft":
            cover_path = os.path.join(compose.MEDIA_DIR,
                                      os.path.basename(pkg["image_url"] or ""))
            if not os.path.exists(cover_path):
                raise HTTPException(409, "封面图缺失，请先重新生成内容包")
            result = publish.wx_publish_draft(
                config["appid"], config["secret"],
                f"{pkg['account_name']}｜{content['title'][:40] if content else '内容'}",
                pkg["copy_text"], cover_path, pkg["account_name"])
            detail = f"草稿已创建（media_id={result['draft_media_id']}），请到 {result['backend']} 查看并点击发布"
        elif channel == "webhook":
            result = publish.webhook_send(config["webhook_url"],
                                          publish.build_payload(pkg, content["title"] if content else ""))
            detail = f"内容包已投递至 Webhook（HTTP {result['status_code']}）"
        else:
            raise HTTPException(409, f"未知通道 {channel}")
    except publish.PublishError as e:
        raise HTTPException(502, str(e))

    db.execute("UPDATE content_packages SET status='published' WHERE id=?", (pid,))
    db.execute("INSERT INTO publish_receipts(package_id,link,note) VALUES(?,?,?)",
               (pid, "", f"[自动] {detail}"))
    db.execute("INSERT INTO events(name,payload_json) VALUES('content_distribute',?)",
               (json.dumps({"package_id": pid, "channel": channel, "auto": True},
                           ensure_ascii=False),))
    return {"ok": True, "channel": channel, "detail": detail}
