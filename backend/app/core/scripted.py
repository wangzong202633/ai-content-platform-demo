# -*- coding: utf-8 -*-
"""Scripted demo content — the offline soul of the demo.

Deterministic, high-quality fallbacks for every LLM task. The pipeline is
cache -> real API -> scripted (here). In offline mode the demo runs entirely
on these, with simulated token streaming, so nothing can die on stage.
"""
import hashlib

# ── design palettes (the visual carrier of the "preference flywheel") ──
DESIGN_V1 = {"bg": "#1B2A4A", "accent": "#C9A45C", "text": "#F5F7FA",
             "layout_note": "深色底金色点缀，庄重商务风"}
DESIGN_V2 = {"bg": "#EAF3F8", "accent": "#2F7FA8", "text": "#1F3340",
             "layout_note": "浅色底大留白，青蓝点缀，国际化轻快"}

# ── invitation: v1 (no light/international rules active) ──
INVITATION_V1 = {
    "title": "诚邀莅临丨2026国际化工装备展",
    "body": ("尊敬的行业同仁：\n\n"
             "我司将携新一代X系列分子筛吸附剂全线产品亮相2026国际化工装备展"
             "（上海·新国际博览中心）。X系列在空分装置能耗优化与天然气深度脱水"
             "两大场景已服务多家头部客户，展会现场提供选型测算与样品咨询。\n\n"
             "展位号：E3-36\n时间：2026年11月18日-21日\n\n"
             "诚挚期待您的莅临指导。"),
    "cta": "扫码预约现场洽谈",
    "design_hint": DESIGN_V1,
}

# ── invitation: v2 (浅色 + 国际化 rules confirmed & injected) ──
INVITATION_V2 = {
    "title": "Connect at ChemEquip 2026 · 与世界共享洁净分离",
    "body": ("Dear Partners / 尊敬的行业同仁：\n\n"
             "2026国际化工装备展，我们在 E3-36 等您。\n\n"
             "新一代 X 系列分子筛吸附剂（X-Series Molecular Sieve）现场首展："
             "空分能耗更低（Lower Energy, Higher Purity），天然气脱水更彻底。"
             "轻设计、大留白，用最简洁的方式讲清每一项性能。\n\n"
             "Nov 18-21 · Shanghai · Booth E3-36\nMeet our team, touch the samples."),
    "cta": "Book a Meeting · 预约洽谈",
    "design_hint": DESIGN_V2,
}

ARTICLE_V1 = {
    "title": "X系列分子筛吸附剂：为空分装置降本的三个关键设计",
    "summary": "从晶格稳定性、传质路径到再生温度，解析X系列如何把空分装置的能耗曲线往下压。",
    "body": ("在空分装置的运行成本里，吸附剂的再生能耗长期是被低估的一项。"
             "X系列分子筛从三个设计维度回应这个问题。\n\n"
             "第一，晶格稳定性。优化铝硅比后骨架在长期水热环境中保持完整，"
             "更换周期延长，摊薄单位处理成本。\n\n"
             "第二，传质路径。颗粒孔道结构缩短了水分扩散距离，"
             "吸附穿透曲线更陡，同样床层高度下处理量提升。\n\n"
             "第三，再生温度窗口。再生温度上限下调，每公斤吸附剂再生能耗下降，"
             "按年运行8000小时测算，单套装置年节约电费可观。\n\n"
             "选型测算与工况数据，欢迎在2026国际化工装备展 E3-36 展位现场交流。"),
    "cta": "阅读全文",
    "design_hint": DESIGN_V1,
}

ARTICLE_V2 = {
    "title": "Clean Air, Lower Cost：X-Series 的三个降本设计",
    "summary": "Three engineering choices inside the X-Series molecular sieve that quietly cut your energy bill.",
    "body": ("再生能耗是空分装置里最容易被忽略的成本项。X-Series 用三个设计把它压下来。\n\n"
             "01 晶格稳定性 Lattice Stability —— 铝硅比优化让骨架在长期水热环境中保持完整，"
             "更换周期更长，单位处理成本更低。\n\n"
             "02 传质路径 Mass Transfer —— 更短的孔道扩散距离带来更陡的穿透曲线，"
             "同等床层高度处理量提升。\n\n"
             "03 再生温度 Regeneration Window —— 再生温度上限下调，"
             "按年运行 8000 小时测算，单套装置电费节约显著。\n\n"
             "Numbers speak. Nov 18-21, Booth E3-36, Shanghai."),
    "cta": "Read More",
    "design_hint": DESIGN_V2,
}

GENERATIONS = {
    ("invitation", "v1"): INVITATION_V1,
    ("invitation", "v2"): INVITATION_V2,
    ("article", "v1"): ARTICLE_V1,
    ("article", "v2"): ARTICLE_V2,
}

# ── preference extraction: the scripted "magic sentence" of the demo ──
MAGIC_FEEDBACK_KEYS = ("颜色太深", "不够国际化")

SIGNAL_LIGHT = {
    "category": "色彩",
    "rule_text": "主色调采用浅色系，避免深色大色块",
    "confidence": 0.93,
    "evidence": "颜色太深",
}
SIGNAL_INTL = {
    "category": "风格",
    "rule_text": "国际化表达，中英文混排点缀，对标国际化工品牌语言",
    "confidence": 0.91,
    "evidence": "不够国际化",
}


def scripted_extract(feedback_text: str):
    """Signals extracted from boss feedback. The demo sentence yields two
    crisp signals; anything else yields one generic signal (still a valid
    demo of the loop)."""
    if all(k in feedback_text for k in MAGIC_FEEDBACK_KEYS):
        return [SIGNAL_LIGHT, SIGNAL_INTL]
    if "颜色" in feedback_text or "深" in feedback_text or "配色" in feedback_text:
        return [dict(SIGNAL_LIGHT, evidence=feedback_text[:24])]
    if "国际化" in feedback_text or "英文" in feedback_text or "国际" in feedback_text:
        return [dict(SIGNAL_INTL, evidence=feedback_text[:24])]
    return [{
        "category": "风格",
        "rule_text": f"避免问题：{feedback_text[:32]}",
        "confidence": 0.62,
        "evidence": feedback_text[:24],
    }]


# ── channel adaptation: deterministic template builders ──
CHANNEL_SPECS = {
    "wechat_mp": {"label": "微信公众号", "size": "900×383", "w": 900, "h": 383, "limit": "标题<64字，摘要<120字"},
    "website":   {"label": "官网 Banner", "size": "1920×600", "w": 1920, "h": 600, "limit": "响应式，精炼+CTA"},
    "channels":  {"label": "视频号（竖版）", "size": "1080×1920", "w": 1080, "h": 1920, "limit": "口播短句"},
    "xhs":       {"label": "小红书", "size": "1080×1080", "w": 1080, "h": 1080, "limit": "标题<20字，轻松+标签"},
    "linkedin":  {"label": "LinkedIn（海外）", "size": "1200×628", "w": 1200, "h": 628, "limit": "专业商务英文"},
}

DEFAULT_CHANNELS = list(CHANNEL_SPECS.keys())


def _clip(text: str, n: int) -> str:
    text = text.strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def scripted_channel_copy(channel: str, body_json: dict) -> dict:
    title = body_json.get("title", "")
    body = body_json.get("body", "")
    cta = body_json.get("cta", "")
    intl = "Connect" in title or "Lower" in body  # v2 marker

    if channel == "wechat_mp":
        digest = body.replace("\n", " ")
        digest = _clip(digest, 110)
        return {"title": _clip(title, 60), "digest": digest, "note": "正式严谨，摘要自动截取"}
    if channel == "website":
        line1 = "X-Series Molecular Sieve" if intl else "新一代X系列分子筛吸附剂"
        return {"headline": _clip(title, 40), "sub": line1, "cta": cta or "了解更多", "note": "精炼大标题+CTA"}
    if channel == "channels":
        hooks = ["空分能耗，再压一档。", "天然气脱水，更彻底。", "X系列，现场首展。", "11.18 上海 E3-36 等你。"] if not intl \
            else ["Lower energy. Higher purity.", "X-Series, first show.", "Nov 18 · Shanghai · E3-36", "Meet our team."]
        return {"hook_lines": hooks, "note": "竖版口播短句"}
    if channel == "xhs":
        t = _clip(title.split("·")[-1].strip() or title, 19)
        return {
            "title": t if t else "化工展逛展攻略",
            "text": ("逛展Day1最惊喜的展位之一👀 深藏功与名的国产吸附剂天花板\n"
                     "能耗数据现场测算，工程师小哥哥超耐心\n"
                     "样品可以上手摸！质感真的可✨\n"
                     "📍E3-36 · 11.18-21 上海"),
            "tags": ["#工业展", "#分子筛", "#化工人日常", "#空分装置"],
            "note": "轻松口语+emoji+标签",
        }
    if channel == "linkedin":
        if intl:
            return {
                "post": ("Clean separation, lower energy. 🌊\n\n"
                         "Meet the X-Series Molecular Sieve at ChemEquip 2026 — "
                         "engineered lattice stability, shorter mass-transfer paths, "
                         "and a wider regeneration window that quietly cuts your energy bill.\n\n"
                         "📍 Nov 18-21 · Shanghai · Booth E3-36\n"
                         "#MolecularSieve #AirSeparation #ChemEquip2026"),
                "note": "Professional EN post",
            }
        return {
            "post": ("Join us at the 2026 International Chemical Equipment Exhibition.\n\n"
                     "Our new-generation X-Series molecular sieve adsorbent will be on "
                     "site: energy optimization for air separation units and deep "
                     "dehydration for natural gas.\n\n"
                     "📍 Nov 18-21 · Shanghai · Booth E3-36"),
            "note": "Formal EN post",
        }
    return {"note": "unknown channel"}


def variant_of(prompt: str) -> str:
    """Prompt hash drives nothing here — rule markers in the prompt decide the
    variant: v2 only when BOTH 浅色(light) AND 国际化(international) rules are
    injected. This is exactly the flywheel made visible."""
    has_light = ("浅色" in prompt) or ("避免深色" in prompt)
    has_intl = "国际化表达" in prompt
    return "v2" if (has_light and has_intl) else "v1"


def display_text(content_type: str, body_json: dict) -> str:
    """The text streamed token-by-token in the UI."""
    if content_type == "invitation":
        return f"{body_json.get('title','')}\n\n{body_json.get('body','')}\n\n{body_json.get('cta','')}"
    return f"{body_json.get('title','')}\n\n{body_json.get('summary','')}\n\n{body_json.get('body','')}"


def key_of(task: str, prompt: str) -> str:
    return hashlib.sha256((task + "\n@@\n" + prompt).encode("utf-8")).hexdigest()
