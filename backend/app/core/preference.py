# -*- coding: utf-8 -*-
"""Preference engine: rule matching/injection + signal extraction + persistence.

Demo-critical behavior: extracted signals NEVER take effect directly — they
become `pending` rules and require supervisor confirmation (PRD 4.4 / Arch
4.5.2). Duplicate signals against existing pending rules are linked, not
re-created.
"""
import json

from .. import db
from . import llm, prompt_engine, scripted


def active_rules() -> list:
    return db.query(
        "SELECT * FROM preference_rules WHERE status='active' ORDER BY id"
    )


def rules_for_injection(content_type: str) -> list:
    """V1.0 keeps <=100 rules; demo injects all active rules (<=8)."""
    return active_rules()


def extract_signals(feedback_text: str, content_summary: str = ""):
    """LLM tier -> scripted fallback. Returns (signals, mode)."""
    prompt = prompt_engine.build_extract_prompt(feedback_text, content_summary)
    obj, mode = llm.complete(
        "pref_extract", prompt, {"signals": scripted.scripted_extract(feedback_text)}
    )
    signals = obj.get("signals", []) if isinstance(obj, dict) else []
    return signals, mode


def _next_code() -> str:
    row = db.query_one("SELECT COUNT(*) AS n FROM preference_rules")
    return f"P{row['n'] + 1:02d}"


def persist_signals(signals: list, source_review_id=None, source_note: str = ""):
    """Create pending rules; link to an identical pending rule instead of
    duplicating. Returns the list of affected rules (pending, awaiting
    supervisor confirmation)."""
    out = []
    for sig in signals:
        cat = sig.get("category", "风格")
        text = sig.get("rule_text", "").strip()
        if not text:
            continue
        # token-aware linking: same category + shared style keyword (浅色/深色/
        # 国际化…) links to the existing pending rule instead of duplicating
        TOKENS = ("浅色", "深色", "留白", "国际化", "简洁", "排版", "正式", "轻松", "创新")
        shared = [t for t in TOKENS if t in text]
        dup = None
        for cand in db.query(
                "SELECT * FROM preference_rules WHERE status IN ('pending','active') AND category=?", (cat,)):
            if (cand["rule_text"] == text or text[:8] in cand["rule_text"]
                    or any(t in cand["rule_text"] for t in shared)):
                dup = cand
                break
        if dup:
            # linked rule: refresh evidence/confidence with the latest feedback
            new_conf = max(float(dup["confidence"]), float(sig.get("confidence", 0) or 0))
            new_ev = sig.get("evidence") or dup["evidence"]
            db.execute("UPDATE preference_rules SET evidence=?, confidence=? WHERE id=?",
                       (new_ev, new_conf, dup["id"]))
            r = db.query_one("SELECT * FROM preference_rules WHERE id=?", (dup["id"],))
            created = False
        else:
            rid = db.execute(
                "INSERT INTO preference_rules(code,category,rule_text,confidence,status,"
                "source_note,source_review_id,evidence) VALUES(?,?,?,?,?,?,?,?)",
                (_next_code(), cat, text, float(sig.get("confidence", 0.8)),
                 "pending", source_note, source_review_id,
                 sig.get("evidence", "")),
            )
            r = db.query_one("SELECT * FROM preference_rules WHERE id=?", (rid,))
            created = True
            db.execute(
                "INSERT INTO events(name,payload_json) VALUES('preference_signal',?)",
                (json.dumps({"rule_id": rid, "code": r["code"], "category": cat,
                             "rule_text": text,
                             "confidence": r["confidence"]}, ensure_ascii=False),),
            )
        out.append({"rule": r, "created": created})
    return out


def confirm(rule_id: int):
    db.execute("UPDATE preference_rules SET status='active' WHERE id=?", (rule_id,))
    r = db.query_one("SELECT * FROM preference_rules WHERE id=?", (rule_id,))
    if r:
        db.execute(
            "INSERT INTO events(name,payload_json) VALUES('preference_confirm',?)",
            (json.dumps({"rule_id": rule_id, "code": r["code"], "action": "confirm"},
                        ensure_ascii=False),),
        )
    return r


def reject(rule_id: int):
    db.execute("UPDATE preference_rules SET status='disabled' WHERE id=?", (rule_id,))
    r = db.query_one("SELECT * FROM preference_rules WHERE id=?", (rule_id,))
    if r:
        db.execute(
            "INSERT INTO events(name,payload_json) VALUES('preference_confirm',?)",
            (json.dumps({"rule_id": rule_id, "code": r["code"], "action": "reject"},
                        ensure_ascii=False),),
        )
    return r
