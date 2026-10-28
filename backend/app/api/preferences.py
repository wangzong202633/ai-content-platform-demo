# -*- coding: utf-8 -*-
"""Preference center APIs: list / extract / confirm / reject."""
from fastapi import APIRouter, HTTPException
import json
from pydantic import BaseModel

from .. import db
from ..core import preference

router = APIRouter()


@router.get("/api/preferences")
def list_preferences(status: str | None = None):
    if status:
        rows = db.query("SELECT * FROM preference_rules WHERE status=? ORDER BY id", (status,))
    else:
        rows = db.query(
            "SELECT * FROM preference_rules ORDER BY CASE status WHEN 'pending' THEN 0 "
            "WHEN 'active' THEN 1 ELSE 2 END, id")
    return rows


class ExtractReq(BaseModel):
    feedback_text: str
    content_id: int | None = None


@router.post("/api/preferences/extract")
def extract(req: ExtractReq):
    if not req.feedback_text.strip():
        raise HTTPException(400, "反馈内容为空")
    summary = ""
    if req.content_id:
        row = db.query_one("SELECT title FROM contents WHERE id=?", (req.content_id,))
        summary = row["title"] if row else ""
    signals, mode = preference.extract_signals(req.feedback_text, summary)
    persisted = preference.persist_signals(
        signals, source_note="偏好中心手动提取" + (f"（内容 #{req.content_id}）" if req.content_id else ""))
    return {"signals": signals, "mode": mode,
            "rules": [{"created": p["created"], "rule": p["rule"]} for p in persisted]}


class EditReq(BaseModel):
    rule_text: str


@router.patch("/api/preferences/{rid}")
def edit_rule(rid: int, req: EditReq):
    """Supervisor manual correction of an extracted rule (risk fallback:
    AI mis-reads the boss's intent → human edits the text before it takes effect)."""
    row = db.query_one("SELECT * FROM preference_rules WHERE id=?", (rid,))
    if not row:
        raise HTTPException(404, "规则不存在")
    text = req.rule_text.strip()
    if not text:
        raise HTTPException(400, "规则文本不能为空")
    db.execute("UPDATE preference_rules SET rule_text=? WHERE id=?", (text, rid))
    db.execute(
        "INSERT INTO events(name,payload_json) VALUES('preference_update',?)",
        (json.dumps({"rule_id": rid, "code": row["code"], "action": "manual_edit"},
                    ensure_ascii=False),))
    return db.query_one("SELECT * FROM preference_rules WHERE id=?", (rid,))


@router.post("/api/preferences/{rid}/confirm")
def confirm(rid: int):
    row = db.query_one("SELECT * FROM preference_rules WHERE id=?", (rid,))
    if not row:
        raise HTTPException(404, "规则不存在")
    if row["status"] != "pending":
        raise HTTPException(409, f"规则 {row['code']} 当前状态为 {row['status']}，无需确认")
    return preference.confirm(rid)


@router.delete("/api/preferences/{rid}")
def reject(rid: int):
    row = db.query_one("SELECT * FROM preference_rules WHERE id=?", (rid,))
    if not row:
        raise HTTPException(404, "规则不存在")
    return preference.reject(rid)
