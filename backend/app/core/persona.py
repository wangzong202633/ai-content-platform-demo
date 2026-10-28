# -*- coding: utf-8 -*-
"""Personal self-media: account personas + scripted persona rewrite fallback.

Live tier uses the text gateway (persona prompt); without a key the scripted
templates below still produce a convincing persona voice — the 'same content,
two faces' story never breaks on stage.
"""
import json

from . import gateway

PLATFORM_LABELS = {
    "wechat_mp_personal": "个人公众号", "channels": "视频号", "xhs": "小红书",
    "douyin": "抖音", "wechat_mp": "公众号(企业)", "website": "官网", "linkedin": "LinkedIn",
}

# platform → poster spec (cover) for content packages
PACKAGE_SPECS = {
    "wechat_mp_personal": {"label": "个人公众号头图", "w": 900, "h": 383, "size": "900×383"},
    "channels": {"label": "视频号竖版", "w": 1080, "h": 1920, "size": "1080×1920"},
    "xhs": {"label": "小红书方图", "w": 1080, "h": 1080, "size": "1080×1080"},
    "douyin": {"label": "抖音竖版", "w": 1080, "h": 1920, "size": "1080×1920"},
}

PERSONA_TEMPLATES = {
    "engineer": {
        "opening": "今天在客户现场又验证了一遍：",
        "closing": "做我们这行的都知道，数据不会说谎。有同行想交流选型参数的，评论区聊。",
        "tags": ["#工程师日常", "#空分装置", "#一线实测", "#工业品"],
        "suggest": "工作日 12:10 或 20:30（工程师刷手机高峰）",
    },
    "boss": {
        "opening": "带团队做出的东西，敢放到世界面前：",
        "closing": "对标国际一线，我们选择用产品说话。下个月上海展会，欢迎来 E3-36 眼见为实。",
        "tags": ["#中国制造", "#走出去", "#化工装备展", "#品牌之路"],
        "suggest": "工作日 07:30（管理者早读时段）",
    },
    "marketing": {
        "opening": "梳理了一份实用向干货：",
        "closing": "完整版放在公众号，评论区扣 1 送选型对照表。",
        "tags": ["#干货分享", "#营销笔记", "#B2B获客", "#内容运营"],
        "suggest": "工作日 18:00（通勤刷屏时段）",
    },
}


def build_persona_prompt(account: dict, content_body: dict) -> str:
    return (
        f"[系统角色] 你是企业员工「{account['name']}」的个人自媒体账号运营者，"
        f"人设：{account['persona']}。平台：{PLATFORM_LABELS.get(account['platform'], account['platform'])}。\n"
        f"[知识注入] 企业定稿内容标题：{content_body.get('title', '')}\n"
        f"正文摘要：{str(content_body.get('body', ''))[:180]}\n"
        f"[任务] 以第一人称、符合人设口吻改写为个人号发布文案（120-200字），"
        f"口语化、有现场感，不复制企业官话。输出 JSON："
        '{"copy":"","tags":["#标签"],"suggest_time":""}'
    )


def _fallback_persona(account: dict, content_body: dict) -> dict:
    tpl = PERSONA_TEMPLATES.get(account.get("persona_key", "engineer"),
                                PERSONA_TEMPLATES["engineer"])
    snip = str(content_body.get("body", ""))[:60].replace("\n", " ").strip()
    return {
        "copy": f"{tpl['opening']}{snip}……\n{tpl['closing']}",
        "tags": tpl["tags"],
        "suggest_time": tpl["suggest"],
    }


def persona_rewrite(account: dict, content_body: dict):
    """Returns (result, mode). mode in {live, scripted}."""
    if not gateway.text_status().get("live"):
        return _fallback_persona(account, content_body), "scripted"
    try:
        prompt = build_persona_prompt(account, content_body)
        text = gateway.chat(prompt, temperature=0.8)
        start, end = text.find("{"), text.rfind("}")
        if start >= 0:
            obj = json.loads(text[start:end + 1])
            if obj.get("copy"):
                return {"copy": obj["copy"],
                        "tags": obj.get("tags") or ["#工业品"],
                        "suggest_time": obj.get("suggest_time", "")}, "live"
    except Exception:
        pass
    return _fallback_persona(account, content_body), "scripted"


def image_prompt(design_hint: dict, platform_label: str) -> str:
    return (
        "浅色系极简工业风背景图，主色调淡云雾蓝，大量留白，"
        "抽象表达洁净空气与天然气处理的轻盈质感，柔和渐变，视觉焦点居中偏右，"
        f"左侧预留排版空间。用于{platform_label}封面背景。"
        "禁止出现任何文字、水印、深色大色块、杂乱元素。"
        "no text, no watermark, light color palette, minimal industrial style, "
        "soft gradient, generous negative space"
    )
