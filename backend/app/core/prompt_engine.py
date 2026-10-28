# -*- coding: utf-8 -*-
"""Prompt engine — the V1.0 "Prompt as code" four-layer assembly.

Layer 1 system role / Layer 2 knowledge injection (brand + active preference
rules + product KB) / Layer 3 task instruction / Layer 4 few-shot example.
Every generation records prompt version + injected rule ids (observability).
"""
from . import scripted

PROMPT_VERSION = "G-1.3"

SYSTEM_ROLE = (
    "你是吸附剂行业B2B企业的资深营销文案专家，服务风格对标巴斯夫等国际化化工"
    "企业的品牌语言。输出必须是可直接使用的营销文案，不要解释你的思考。"
)

PRODUCT_KB = (
    "## 品牌规范（来源：品牌知识库 v2026.10）\n"
    "- 文案禁止夸大性能承诺，技术表述需可溯源至产品知识库\n"
    "- 视觉与语言风格必须与下方生效偏好规则保持一致\n"
    "- 全球市场表达规范参照生效偏好规则执行\n\n"
    "## 产品知识（来源：产品知识库 v2026.10）\n"
    "- X系列分子筛吸附剂：优化铝硅比，晶格稳定性提升，更换周期延长\n"
    "- 两大核心场景：空分装置能耗优化 / 天然气深度脱水\n"
    "- 数据点：年运行8000小时测算，再生能耗显著下降\n"
    "- 展会：2026国际化工装备展 · 上海 · 11月18-21日 · 展位E3-36"
)

FEWSHOT = (
    "## 参考样例（脱敏）\n"
    '{"title":"Meet Us at Booth E3-36","body":"新一代X系列分子筛…",'
    '"cta":"Book a Meeting","design_hint":{"bg":"#EAF3F8","accent":"#2F7FA8"}}'
)


def build_generation_prompt(content_type: str, params: dict, active_rules: list) -> str:
    rules_block = "\n".join(
        f"- [{r['code']}] {r['category']}｜{r['rule_text']}" for r in active_rules
    ) or "-（暂无生效偏好规则）"

    if content_type == "invitation":
        task = (
            "## 任务\n为「2026国际化工装备展」生成观众邀请函。输出 JSON：\n"
            '{"title":"","body":"","cta":"","design_hint":{"bg":"","accent":"","text":"","layout_note":""}}\n'
            "要求：正文150-250字；必须包含展位号 E3-36 与两个核心卖点（空分能耗优化、天然气深度脱水）；"
            "design_hint 的 bg/accent/text 为十六进制颜色，必须严格遵守上方生效偏好规则中的色彩与风格约束。"
        )
    else:
        task = (
            "## 任务\n生成一篇公众号文章。输出 JSON：\n"
            '{"title":"","summary":"","body":"","cta":"","design_hint":{"bg":"","accent":"","text":"","layout_note":""}}\n'
            "要求：正文300-450字，分段清晰；突出专业性与数据；颜色同样严格遵守生效偏好规则。"
        )

    info = "\n".join(f"- {k}: {v}" for k, v in params.items() if v)
    lang_rule = (
        "\n\n## 语言风格硬性约束\n"
        "仅当上方生效偏好规则中明确包含「国际化表达」类规则时，标题与正文才允许并【必须】使用中英混排"
        "（标题格式如「Connect at ChemEquip 2026 · 中文主题」，正文穿插 1-2 处英文短语）；"
        "否则必须使用正式中文商务语言，标题与正文不得出现任何英文单词。"
    )
    return (
        f"[第一层·系统角色]\n{SYSTEM_ROLE}\n\n"
        f"[第二层·知识注入]\n## 本次生效的老板偏好规则\n{rules_block}\n\n"
        f"{PRODUCT_KB}\n\n[补充信息]\n{info}{lang_rule}\n\n"
        f"[第三层·任务指令]\n{task}\n\n[第四层·示例引导]\n{FEWSHOT}"
    )


def build_extract_prompt(feedback_text: str, content_summary: str) -> str:
    return (
        "[第一层·系统角色]\n你是偏好信号提取器，从老板审核反馈中提取可执行的偏好规则。\n\n"
        f"[第二层·知识注入]\n内容摘要：{content_summary[:120]}\n\n"
        "[第三层·任务指令]\n分析以下反馈，输出 JSON：\n"
        '{"signals":[{"category":"色彩|风格|排版|内容|标杆","rule_text":"可执行的规则化表述",'
        '"confidence":0.0,"evidence":"反馈原文引用"}]}\n'
        "硬性要求：1)最多输出2条信号；2)颜色/配色类问题归入「色彩」类别，语言风格/国际化类问题归入「风格」类别，"
        "两类问题同时出现时必须拆成两条独立信号；3)规则表述必须具体可执行（如\"主色调采用浅色系，避免深色大色块\"而非\"颜色好看点\"）。\n\n"
        f"[反馈原文]\n{feedback_text}"
    )


def build_channel_prompt(channel: str, body_json: dict) -> str:
    spec = scripted.CHANNEL_SPECS[channel]
    return (
        f"[系统角色] 你是{spec['label']}渠道的资深运营文案。\n"
        f"[知识注入] 渠道规格：{spec['size']}，{spec['limit']}。\n"
        f"定稿内容：{body_json.get('title','')}｜{str(body_json.get('body',''))[:150]}\n"
        f"[任务] 输出适配该渠道的文案 JSON（风格遵循渠道人格："
        f"{'英文专业商务' if channel=='linkedin' else '轻松口语' if channel=='xhs' else '口播短句' if channel=='channels' else '正式精炼'}）。"
    )
