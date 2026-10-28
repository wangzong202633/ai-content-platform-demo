# -*- coding: utf-8 -*-
"""Content APIs: SSE generation, manual editing, urgent flag, multi-channel
adaptation, review loop."""
import json
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .. import db
from ..core import llm, preference, prompt_engine, scripted, workflow

router = APIRouter()

TYPE_LABELS = {"invitation": "展会邀请函", "article": "公众号文章"}


def _content_row(c: dict) -> dict:
    c = dict(c)
    c["type_label"] = TYPE_LABELS.get(c["type"], c["type"])
    c["status_label"] = workflow.STATUSES.get(c["status"], c["status"])
    for k, dst in (("body_json", "body"), ("params_json", "params"),
                   ("used_preference_ids_json", "used_preference_ids"),
                   ("generation_meta_json", "generation_meta")):
        try:
            c[dst] = json.loads(c.get(k) or "{}") if k.endswith("json") and dst != "used_preference_ids" else (
                json.loads(c.get(k) or "[]") if k == "used_preference_ids_json" else {})
        except Exception:
            c[dst] = {} if k != "used_preference_ids_json" else []
        c.pop(k, None)
    c["design_hint"] = c["body"].get("design_hint", {}) if isinstance(c["body"], dict) else {}
    return c


def get_content(cid: int) -> dict:
    row = db.query_one("SELECT * FROM contents WHERE id=?", (cid,))
    if not row:
        raise HTTPException(404, f"内容 #{cid} 不存在")
    return _content_row(row)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class GenerateReq(BaseModel):
    type: str = "invitation"
    topic: str = ""
    event_name: str = "2026国际化工装备展"
    sellpoints: str = ""
    base_content_id: int | None = None
    is_urgent: bool = False


def _hex_lum(hex_color: str) -> float:
    h = (hex_color or "").lstrip("#")
    if len(h) != 6:
        return 0.5
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _enforce_palette(body_obj: dict, rules: list) -> dict:
    """Design guard: live-LLM safety net, symmetric both ways.
    - 浅色(light) rule injected but model returned dark  -> enforce light palette
    - no light rule yet (v1 era) but model returned light -> enforce corporate
      dark palette, so the v1-dark / v2-light flywheel story stays
      deterministic even with a live model."""
    has_light = any(("浅色" in r["rule_text"]) or ("非深色" in r["rule_text"])
                    or ("避免深色" in r["rule_text"]) for r in rules)
    dh = body_obj.get("design_hint") or {}
    lum = _hex_lum(dh.get("bg", ""))
    if has_light and lum < 0.55:
        dh = {**dh, "bg": "#EAF3F8", "accent": "#2F7FA8", "text": "#1F3340",
              "layout_note": "浅色底大留白，青蓝点缀，国际化轻快"}
    elif not has_light and lum >= 0.55:
        dh = {**dh, "bg": "#1B2A4A", "accent": "#C9A45C", "text": "#F5F7FA",
              "layout_note": "深色底金色点缀，庄重商务风"}
    body_obj["design_hint"] = dh
    return body_obj


@router.post("/api/contents/generate")
def generate(req: GenerateReq):
    if req.type not in TYPE_LABELS:
        raise HTTPException(400, f"不支持的内容类型 {req.type}")

    rules = preference.rules_for_injection(req.type)
    params = {"主题": req.topic or TYPE_LABELS[req.type],
              "展会/场景": req.event_name, "核心卖点": req.sellpoints or "空分能耗优化、天然气深度脱水"}

    if req.base_content_id:
        base = get_content(req.base_content_id)
        version = base["version"] + 1
        lineage = base["params"].get("lineage_root", base["id"])
        params = {**base["params"], **{k: v for k, v in params.items() if v}}
        params["lineage_root"] = lineage
    else:
        version = 1
        params["lineage_root"] = None  # set to own id after insert

    # F11 急单快速通道（最小版）：标记 + 4小时 SLA（PRD：急单端到端交付 < 4 小时，当日交付）
    if req.is_urgent:
        params["is_urgent"] = True
        params["urgent_deadline"] = (datetime.now() + timedelta(hours=4)).strftime(
            "%Y-%m-%d %H:%M:%S")

    prompt = prompt_engine.build_generation_prompt(req.type, params, rules)
    body_obj, mode = llm.complete(
        f"gen_{req.type}", prompt,
        scripted.GENERATIONS[(req.type, scripted.variant_of(prompt))],
    )
    body_obj = _enforce_palette(body_obj, rules)
    rule_ids = [r["id"] for r in rules]

    cid = db.execute(
        "INSERT INTO contents(project_id,type,title,status,version,params_json,"
        "used_preference_ids_json) VALUES(?,?,?,?,?,?,?)",
        (1, req.type, body_obj.get("title", ""), "generating", version,
         json.dumps(params, ensure_ascii=False), json.dumps(rule_ids)),
    )
    if not params.get("lineage_root"):
        db.execute("UPDATE contents SET params_json=? WHERE id=?",
                   (json.dumps({**params, "lineage_root": cid}, ensure_ascii=False), cid))
        params["lineage_root"] = cid
    db.execute("INSERT INTO events(name,payload_json) VALUES('content_create',?)",
               (json.dumps({"content_id": cid, "type": req.type, "version": version},
                           ensure_ascii=False),))
    db.execute("INSERT INTO events(name,payload_json) VALUES('ai_generate_start',?)",
               (json.dumps({"content_id": cid, "preferences_applied": len(rule_ids)},
                           ensure_ascii=False),))
    if req.is_urgent:
        db.execute("INSERT INTO events(name,payload_json) VALUES('urgent_order',?)",
                   (json.dumps({"content_id": cid, "deadline": params["urgent_deadline"],
                                "source": "supervisor"}, ensure_ascii=False),))

    def stream():
        started = time.time()
        yield _sse("meta", {
            "content_id": cid, "type": req.type, "version": version, "mode": mode,
            "model": llm.stats()["model"],
            "is_urgent": bool(params.get("is_urgent")),
            "urgent_deadline": params.get("urgent_deadline"),
            "used_preferences": [
                {"id": r["id"], "code": r["code"], "category": r["category"],
                 "rule_text": r["rule_text"]} for r in rules],
        })
        text = scripted.display_text(req.type, body_obj)
        for chunk in llm.stream_tokens(text):
            yield _sse("token", {"text": chunk})
        meta = {"prompt_version": prompt_engine.PROMPT_VERSION,
                "latency_ms": int((time.time() - started) * 1000),
                "tokens": len(text) // 2, "mode": mode,
                "injected_rules": [r["code"] for r in rules]}
        db.execute(
            "UPDATE contents SET title=?, body_json=?, status='pending_supervisor', "
            "generation_meta_json=? WHERE id=?",
            (body_obj.get("title", ""), json.dumps(body_obj, ensure_ascii=False),
             json.dumps(meta, ensure_ascii=False), cid))
        db.execute("INSERT INTO events(name,payload_json) VALUES('ai_generate_complete',?)",
                   (json.dumps({"content_id": cid, "latency_ms": meta["latency_ms"]},
                               ensure_ascii=False),))
        yield _sse("done", {"content": get_content(cid)})

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class EditReq(BaseModel):
    title: str | None = None
    body: str | None = None
    summary: str | None = None
    cta: str | None = None


@router.put("/api/contents/{cid}")
def edit_content(cid: int, req: EditReq):
    """Manual polish of AI draft (PRD 4.2 内容专员基于AI初稿人工加工).
    Allowed before distribution; every edit logs the content_edit event."""
    c = get_content(cid)
    if c["status"] in ("generating", "distributed"):
        raise HTTPException(409, "当前状态不可编辑（生成中 / 已分发）")
    body_obj = dict(c["body"])
    edited = []
    for field in ("title", "body", "cta", "summary"):
        new_val = getattr(req, field)
        if new_val is not None and new_val.strip() and new_val.strip() != body_obj.get(field):
            body_obj[field] = new_val.strip()
            edited.append(field)
    if not edited:
        raise HTTPException(400, "没有需要保存的修改")
    meta = dict(c["generation_meta"] or {})
    meta["has_manual_edit"] = True
    db.execute(
        "UPDATE contents SET title=?, body_json=?, generation_meta_json=? WHERE id=?",
        (body_obj.get("title", c["title"]), json.dumps(body_obj, ensure_ascii=False),
         json.dumps(meta, ensure_ascii=False), cid))
    db.execute("INSERT INTO events(name,payload_json) VALUES('content_edit',?)",
               (json.dumps({"content_id": cid, "edit_type": "manual_polish",
                            "edit_extent": len(edited), "fields": edited},
                           ensure_ascii=False),))
    return get_content(cid)


class AdaptReq(BaseModel):
    channels: list[str] | None = None


@router.post("/api/contents/{cid}/adapt")
def adapt(cid: int, req: AdaptReq):
    c = get_content(cid)
    if c["status"] in ("draft", "generating"):
        raise HTTPException(409, "内容尚未生成完成")
    channels = req.channels or scripted.DEFAULT_CHANNELS
    versions = []
    for ch in channels:
        spec = scripted.CHANNEL_SPECS.get(ch)
        if not spec:
            continue
        prompt = prompt_engine.build_channel_prompt(ch, c["body"])
        base_copy = scripted.scripted_channel_copy(ch, c["body"])
        copy_obj, mode = llm.complete(
            f"channel_{ch}", prompt, base_copy)
        if mode in ("api", "cache") and isinstance(copy_obj, dict):
            # schema-stable overlay: scripted template guarantees keys (tags/hooks/...),
            # live model fields win only when non-empty (cache stores raw live output,
            # so cached entries need the same guard)
            copy_obj = {**base_copy, **{k: v for k, v in copy_obj.items() if v}}
        db.execute("DELETE FROM channel_versions WHERE content_id=? AND channel=?", (cid, ch))
        db.execute(
            "INSERT INTO channel_versions(content_id,channel,copy_json,spec_json) VALUES(?,?,?,?)",
            (cid, ch, json.dumps(copy_obj, ensure_ascii=False),
             json.dumps({"w": spec["w"], "h": spec["h"], "size": spec["size"],
                         "limit": spec["limit"], "label": spec["label"]},
                        ensure_ascii=False)))
        versions.append({"channel": ch, "label": spec["label"], "size": spec["size"],
                         "limit": spec["limit"], "w": spec["w"], "h": spec["h"],
                         "copy": copy_obj, "mode": mode})
    db.execute("INSERT INTO events(name,payload_json) VALUES('multi_channel_adapt',?)",
               (json.dumps({"content_id": cid, "channels": channels,
                            "success_count": len(versions)}, ensure_ascii=False),))
    return {"content_id": cid, "versions": versions}


class ReviewReq(BaseModel):
    role: str
    action: str
    feedback_text: str = ""


@router.post("/api/contents/{cid}/review")
def review(cid: int, req: ReviewReq):
    c = get_content(cid)
    try:
        nxt = workflow.transition(c["status"], req.role, req.action)
    except ValueError as e:
        raise HTTPException(409, str(e))

    prior_boss = db.query(
        "SELECT COUNT(*) AS n FROM reviews WHERE content_id=? AND reviewer_role='boss'", (cid,)
    )[0]["n"]
    round_no = prior_boss + 1 if req.role == "boss" else 1
    rid = db.execute(
        "INSERT INTO reviews(content_id,reviewer_role,action,feedback_text,round) VALUES(?,?,?,?,?)",
        (cid, req.role, req.action, req.feedback_text, round_no))
    db.execute("UPDATE contents SET status=? WHERE id=?", (nxt, cid))
    db.execute(
        "INSERT INTO events(name,payload_json) VALUES(?,?)",
        (f"review_{req.action}",
         json.dumps({"content_id": cid, "reviewer_role": req.role, "round": round_no,
                     "reject_reason": req.feedback_text[:60]} if req.action == "reject"
                    else {"content_id": cid, "reviewer_role": req.role, "round": round_no},
                    ensure_ascii=False)))

    extracted = []
    if req.action == "reject":
        signals, _ = preference.extract_signals(req.feedback_text, c["title"])
        extracted = preference.persist_signals(
            signals, source_review_id=rid, source_note=f"内容 #{cid} {c['type_label']} 退回反馈")

    return {"content": get_content(cid),
            "extracted": [{"created": e["created"], "rule": e["rule"]} for e in extracted]}


@router.post("/api/contents/{cid}/distribute")
def distribute(cid: int):
    c = get_content(cid)
    try:
        nxt = workflow.transition(c["status"], "supervisor", "distribute")
    except ValueError as e:
        raise HTTPException(409, str(e))
    db.execute("UPDATE contents SET status=? WHERE id=?", (nxt, cid))
    rows = db.query("SELECT channel FROM channel_versions WHERE content_id=?", (cid,))
    for r in rows:
        db.execute("INSERT INTO events(name,payload_json) VALUES('content_distribute',?)",
                   (json.dumps({"content_id": cid, "channel": r["channel"]}, ensure_ascii=False),))
    return {"content": get_content(cid), "channels": [r["channel"] for r in rows]}


@router.get("/api/contents")
def list_contents(status: str | None = None, project_id: int | None = None):
    sql, args = "SELECT * FROM contents", []
    conds = []
    if status:
        conds.append("status=?"); args.append(status)
    if project_id:
        conds.append("project_id=?"); args.append(project_id)
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY id DESC"
    return [ _content_row(r) for r in db.query(sql, args) ]


@router.get("/api/contents/{cid}")
def content_detail(cid: int):
    c = get_content(cid)
    c["channel_versions"] = [
        {"channel": v["channel"],
         "copy": json.loads(v["copy_json"] or "{}"),
         "spec": json.loads(v["spec_json"] or "{}")}
        for v in db.query(
            "SELECT * FROM channel_versions WHERE content_id=? ORDER BY id", (cid,))]
    c["reviews"] = db.query(
        "SELECT * FROM reviews WHERE content_id=? ORDER BY id DESC", (cid,))
    rule_ids = c["used_preference_ids"]
    if rule_ids:
        marks = ",".join("?" * len(rule_ids))
        c["applied_rules"] = db.query(
            f"SELECT * FROM preference_rules WHERE id IN ({marks})", rule_ids)
    else:
        c["applied_rules"] = []
    # lineage versions (v1/v2 compare view)
    root = c["params"].get("lineage_root") or cid
    c["lineage"] = [ _content_row(r) for r in db.query(
        "SELECT * FROM contents WHERE id=? OR json_extract(params_json,'$.lineage_root')=? "
        "ORDER BY version", (root, root)) ]
    return c
