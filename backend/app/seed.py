# -*- coding: utf-8 -*-
"""Seed data — the demo starts with 'history', not an empty warehouse."""
import json
from datetime import datetime, timedelta

from . import db


def seed():
    if db.query_one("SELECT id FROM projects LIMIT 1"):
        seed_accounts()
        return  # already seeded

    now = datetime.now()
    days_ago = lambda d: (now - timedelta(days=d)).strftime("%Y-%m-%d %H:%M:%S")

    pid = db.execute(
        "INSERT INTO projects(name,type,status,deadline) VALUES(?,?,?,?)",
        ("2026国际化工装备展", "展会", "active", "2026-11-18"),
    )

    # historical distributed content (deep-tone era, feeds the dashboard)
    c1 = db.execute(
        "INSERT INTO contents(project_id,type,title,body_json,status,version,"
        "used_preference_ids_json,generation_meta_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (pid, "article", "为什么空分装置的能耗账要重新算",
         json.dumps({"title": "为什么空分装置的能耗账要重新算", "summary": "一次关于再生能耗的成本重构。",
                     "body": "……（历史内容）", "design_hint": {"bg": "#1B2A4A", "accent": "#C9A45C",
                                                                "text": "#F5F7FA", "layout_note": "深色商务"}},
                     ensure_ascii=False),
         "distributed", 1, "[]", "{}", days_ago(26)),
    )
    c2 = db.execute(
        "INSERT INTO contents(project_id,type,title,body_json,status,version,"
        "used_preference_ids_json,generation_meta_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (pid, "invitation", "诚邀莅临丨2026华南化工新材料展",
         json.dumps({"title": "诚邀莅临丨2026华南化工新材料展", "body": "……（历史内容）",
                     "cta": "扫码预约", "design_hint": {"bg": "#20304F", "accent": "#C9A45C",
                                                        "text": "#F5F7FA", "layout_note": "深色商务"}},
                     ensure_ascii=False),
         "distributed", 2, "[]", "{}", days_ago(12)),
    )
    # a review trail: c1 passed first try (feeds the pass-rate numerator)
    db.execute("INSERT INTO reviews(content_id,reviewer_role,action,feedback_text,round,created_at)"
               " VALUES(?,?,?,?,?,?)", (c1, "supervisor", "approve", "", 1, days_ago(26)))
    db.execute("INSERT INTO reviews(content_id,reviewer_role,action,feedback_text,round,created_at)"
               " VALUES(?,?,?,?,?,?)", (c1, "boss", "approve", "", 1, days_ago(25)))
    # c2 went through 2 boss rounds before approval
    db.execute("INSERT INTO reviews(content_id,reviewer_role,action,feedback_text,round,created_at)"
               " VALUES(?,?,?,?,?,?)", (c2, "supervisor", "approve", "", 1, days_ago(11)))
    db.execute("INSERT INTO reviews(content_id,reviewer_role,action,feedback_text,round,created_at)"
               " VALUES(?,?,?,?,?,?)",
               (c2, "boss", "reject", "标题不够大气，重点不突出", 1, days_ago(10)))
    db.execute("INSERT INTO reviews(content_id,reviewer_role,action,feedback_text,round,created_at)"
               " VALUES(?,?,?,?,?,?)", (c2, "boss", "approve", "", 2, days_ago(9)))

    # an article waiting for supervisor review (inbox not empty on open)
    c3 = db.execute(
        "INSERT INTO contents(project_id,type,title,body_json,status,version,"
        "used_preference_ids_json,generation_meta_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (pid, "article", "天然气深度脱水：选型时最容易被忽略的三个参数",
         json.dumps({"title": "天然气深度脱水：选型时最容易被忽略的三个参数",
                     "summary": "露点、床层高度与再生窗口的组合决定了脱水深度。",
                     "body": "……（AI初稿正文，演示时从审核中心打开）",
                     "cta": "阅读全文",
                     "design_hint": {"bg": "#1B2A4A", "accent": "#C9A45C", "text": "#F5F7FA",
                                     "layout_note": "深色商务"}},
                    ensure_ascii=False),
         "pending_supervisor", 1, "[3,4,5,6]",
         json.dumps({"prompt_version": "G-1.3", "latency_ms": 38200, "mode": "cache"},
                    ensure_ascii=False),
         days_ago(1)),
    )

    # preference rules: 4 active + 1 pending (P01 浅色系 — last month's signal,
    # awaiting confirmation; the flywheel's first turn is one click away)
    rules = [
        ("P01", "色彩", "主色调采用浅色系，避免深色大色块", 0.88, "pending",
         "上月展会海报反馈提取，待主管确认", "深色看久了闷"),
        ("P02", "排版", "简洁留白，信息密度低", 0.95, "active", "主管初始录入", ""),
        ("P03", "内容", "突出创新元素与新品首发", 0.93, "active", "主管初始录入", ""),
        ("P04", "标杆", "视觉语言对标巴斯夫", 0.9, "active", "主管初始录入", ""),
        ("P05", "内容", "专业深度适中，用数据支撑卖点", 0.92, "active", "主管初始录入", ""),
        ("P06", "风格", "正式商务语气", 0.9, "active", "主管初始录入", ""),
    ]
    for code, cat, text, conf, status, note, ev in rules:
        db.execute(
            "INSERT INTO preference_rules(code,category,rule_text,confidence,status,source_note,evidence)"
            " VALUES(?,?,?,?,?,?,?)", (code, cat, text, conf, status, note, ev))

    seed_accounts()

    for name, payload in [
        ("content_create", {"type": "article"}),
        ("ai_generate_complete", {"type": "article", "latency_ms": 38200}),
        ("content_distribute", {"channel": "wechat_mp"}),
    ]:
        db.execute("INSERT INTO events(name,payload_json) VALUES(?,?)",
                   (name, json.dumps(payload, ensure_ascii=False)))


def seed_accounts():
    if db.query_one("SELECT id FROM accounts LIMIT 1"):
        return
    for name, platform, persona_t, key, followers, owner in [
        ("张工·一线笔记", "xhs", "一线工程师人设：实干、口语、带现场感", "engineer", 8600, "销售工程师张工"),
        ("陈总说制造", "channels", "企业掌舵人：国际视野、品牌自信", "boss", 5200, "总经理"),
        ("Maggie的B2B营销笔记", "wechat_mp_personal", "市场营销人设：干货、方法论、轻专业", "marketing", 3100, "市场主管"),
        ("吸附科技官号", "wechat_mp", "企业官方：严谨、国际化", "official", 12500, "市场部"),
    ]:
        db.execute(
            "INSERT INTO accounts(name,platform,persona,persona_key,followers,owner,auth_status)"
            " VALUES(?,?,?,?,?,?,?)", (name, platform, persona_t, key, followers, owner, "authorized"))
