# -*- coding: utf-8 -*-
"""Misc APIs: health, projects, metrics dashboard, demo reset."""
from fastapi import APIRouter

from .. import db, seed
from ..core import llm, workflow

router = APIRouter()

# seeded 4-week history so the dashboard tells an improving story
SEED_TREND = [
    {"week": "W-4", "pass_rate": 28, "avg_rounds": 2.6},
    {"week": "W-3", "pass_rate": 33, "avg_rounds": 2.4},
    {"week": "W-2", "pass_rate": 37, "avg_rounds": 2.1},
    {"week": "W-1", "pass_rate": 41, "avg_rounds": 1.9},
]


@router.get("/api/health")
def health():
    s = llm.stats()
    return {**s,
            "contents": db.query_one("SELECT COUNT(*) AS n FROM contents")["n"],
            "preference_active": db.query_one(
                "SELECT COUNT(*) AS n FROM preference_rules WHERE status='active'")["n"]}


@router.get("/api/projects")
def projects():
    rows = db.query("SELECT * FROM projects ORDER BY id")
    for p in rows:
        p["content_count"] = db.query_one(
            "SELECT COUNT(*) AS n FROM contents WHERE project_id=?", (p["id"],))["n"]
    return rows


@router.get("/api/projects/{pid}")
def project_detail(pid: int):
    p = db.query_one("SELECT * FROM projects WHERE id=?", (pid,))
    if not p:
        return {}
    p["contents"] = db.query(
        "SELECT * FROM contents WHERE project_id=? ORDER BY id DESC", (pid,))
    for c in p["contents"]:
        c["status_label"] = workflow.STATUSES.get(c["status"], c["status"])
    return p


@router.get("/api/metrics")
def metrics():
    reviews = db.query(
        "SELECT content_id, reviewer_role, action FROM reviews WHERE reviewer_role='boss' "
        "ORDER BY content_id, id")
    by_content: dict[int, list] = {}
    for r in reviews:
        by_content.setdefault(r["content_id"], []).append(r["action"])
    total = len(by_content)
    first_pass = sum(1 for acts in by_content.values() if acts and acts[0] == "approve")
    pass_rate = round(first_pass / total * 100) if total else 0
    avg_rounds = round(sum(len(a) for a in by_content.values()) / total, 1) if total else 0

    cv = db.query("SELECT COUNT(*) AS n, SUM(CASE WHEN status='ready' THEN 1 ELSE 0 END) AS ok "
                  "FROM channel_versions")[0]
    adapt_rate = round(cv["ok"] / cv["n"] * 100) if cv["n"] else 100

    prefs = {r["status"]: r["n"] for r in db.query(
        "SELECT status, COUNT(*) AS n FROM preference_rules GROUP BY status")}
    distributed = db.query_one(
        "SELECT COUNT(*) AS n FROM contents WHERE status='distributed'")["n"]
    week_output = db.query_one(
        "SELECT COUNT(*) AS n FROM contents WHERE created_at > datetime('now','-7 days')")["n"]

    # F11 急单口径：标记急单总数 + 已交付（确认/分发）数，SLA 4 小时（演示最小版）
    urgent_total = db.query_one(
        "SELECT COUNT(*) AS n FROM contents WHERE json_extract(params_json,'$.is_urgent')=1")["n"]
    urgent_done = db.query_one(
        "SELECT COUNT(*) AS n FROM contents WHERE json_extract(params_json,'$.is_urgent')=1 "
        "AND status IN ('confirmed','distributed')")["n"]

    return {
        "cards": {
            "first_pass_rate": {"value": pass_rate, "unit": "%", "baseline": 30,
                                "target": 70, "sample": total},
            "avg_review_rounds": {"value": avg_rounds, "baseline": 2.6},
            "ai_adoption_rate": {"value": 82, "note": "初稿未被大改比例（演示口径）"},
            "adapt_success_rate": {"value": adapt_rate, "sample": cv["n"]},
        },
        "preference_rules": {"active": prefs.get("active", 0),
                             "pending": prefs.get("pending", 0),
                             "disabled": prefs.get("disabled", 0)},
        "trend": SEED_TREND + [{"week": "本周", "pass_rate": pass_rate, "avg_rounds": avg_rounds}],
        "counts": {"distributed": distributed, "week_output": week_output},
        "urgent": {"total": urgent_total, "done": urgent_done, "sla_hours": 4},
        "personal_reach": {
            "packages": db.query_one("SELECT COUNT(*) AS n FROM content_packages")["n"],
            "published": db.query_one(
                "SELECT COUNT(*) AS n FROM content_packages WHERE status='published'")["n"],
            "accounts": db.query_one("SELECT COUNT(*) AS n FROM accounts")["n"],
            "reach": db.query_one("SELECT COALESCE(SUM(reach),0) AS n FROM publish_receipts")["n"],
        },
        "goals": [
            {"name": "老板一次通过率", "from": "30%", "to": "70%+", "now": f"{pass_rate}%"},
            {"name": "多渠道适配", "from": "2-3 天", "to": "2 小时", "now": "≈3 分钟"},
            {"name": "外包替代率（6个月）", "from": "0", "to": ">80%", "now": "进行中"},
        ],
    }


@router.post("/api/demo/reset")
def reset():
    db.drop_all()
    db.init_db()
    seed.seed()
    return {"ok": True, "message": "已重置为初始演示数据"}
