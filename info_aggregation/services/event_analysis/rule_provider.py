from collections import Counter
import re

from services.collection.acquisition_quality import build_acquisition_quality_profile
from services.quality.data_quality import is_low_value_content

from .schemas import EventAnalysisResult, EventFact, TimelinePoint
from .text_utils import clean_source_text, ensure_sentence_end, natural_clip, remove_title_prefix, split_sentences, text_similarity


TECH_TOPIC_LABELS = {
    "chip_release": "芯片发布",
    "model_release": "模型发布",
    "dev_tool": "开发工具",
}

NOISY_SUMMARY_MARKERS = (
    "#",
    "全家都爱",
    "巨巨",
    "好喝",
    "教会你",
    "种草",
    "我的观影报告",
    "电影推荐",
    "精彩片段",
    "盘后，最大的",
    "聊热点",
    "划下红线",
    "悲催了",
    "快讯！",
    "流言板",
    "大利好",
)

PUBLIC_EVENT_MARKERS = (
    "通报",
    "辟谣",
    "假的",
    "事故",
    "伤亡",
    "出院",
    "救援",
    "坠海",
    "坠落",
    "失踪",
    "爆炸",
    "火灾",
    "起诉",
    "违法",
    "偷拍",
    "公务员",
    "调查",
    "回应",
    "宣布",
    "退出",
    "访华",
    "会晤",
    "磋商",
    "会议",
    "政策",
    "监管",
    "法院",
    "警方",
    "消防",
    "官方",
    "公权力",
    "下调",
    "上涨",
    "降雨",
    "暴雨",
    "存款利息",
    "比赛",
    "半决赛",
    "季后赛",
    "总分",
    "大胜",
    "转播",
)


def _split_csv(raw_value: str) -> list[str]:
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _top_values(items, attr_name: str, limit: int = 3) -> list[str]:
    counter: Counter[str] = Counter()
    for item in items:
        counter.update(_split_csv(getattr(item, attr_name, "") or ""))
    return [value for value, _ in counter.most_common(limit)]


def _top_topic(items) -> str:
    counter: Counter[str] = Counter(item.tech_topic_type for item in items if item.tech_topic_type)
    if not counter:
        return ""
    topic = counter.most_common(1)[0][0]
    return TECH_TOPIC_LABELS.get(topic, topic)


def _source_count(items) -> int:
    return len({item.channel_id for item in items if item.channel_id})


def _item_count(items) -> int:
    return len({item.id for item in items if item.id}) or len(items)


def _category_code(item) -> str:
    return item.category.code if getattr(item, "category", None) else ""


def _channel_name(item) -> str:
    return item.channel.name if getattr(item, "channel", None) else "当前来源"


def _looks_like_noisy_sentence(text: str) -> bool:
    value = text or ""
    if any(marker in value for marker in NOISY_SUMMARY_MARKERS):
        return True
    if re.search(r"[#＃][^#＃]{1,24}[#＃]?", value):
        return True
    if len(value) >= 80 and " " not in value and not any(punctuation in value for punctuation in "，。；：！？,.!?"):
        return True
    return False


def _title_based_event_summary(item) -> str:
    title = clean_source_text(item.title or "").rstrip("。！？!?")
    if not title:
        return ""
    channel_name = _channel_name(item)

    if any(marker in title for marker in ("辟谣", "假的")):
        return ensure_sentence_end(f"{title}，相关传言正在被核验，后续应以官方和权威来源为准")
    if any(marker in title for marker in ("事故", "伤亡", "出院", "救援", "坠", "失踪", "爆炸", "火灾", "消防", "暴雨", "降雨")):
        return ensure_sentence_end(f"{title}，事件涉及公共安全和后续处置，需持续关注权威通报")
    if any(marker in title for marker in ("起诉", "违法", "偷拍", "公务员", "法院", "警方")):
        return ensure_sentence_end(f"{title}，事件涉及公共治理或法律处置，后续应以权威披露为准")
    if any(marker in title for marker in ("访华", "会晤", "磋商", "会议", "台独", "经贸", "关税", "制裁", "政策")):
        return ensure_sentence_end(f"{title}，事件涉及公共政策和外部关系变化，后续进展值得关注")
    if any(marker in title for marker in ("存款利息", "下调", "上涨")):
        return ensure_sentence_end(f"{title}，事件涉及民生经济或市场变化，后续影响仍需结合更多来源验证")
    if any(marker in title for marker in ("退出", "转播", "比赛", "半决赛", "季后赛", "总分", "大胜", "男篮", "女足", "国乒", "马刺")):
        return ensure_sentence_end(f"{title}，事件涉及体育赛程或队伍变化，后续安排仍需关注")
    if any(marker in title for marker in ("AI", "芯片", "存储", "腾讯", "马化腾", "OpenAI", "模型")):
        return ensure_sentence_end(f"{title}，事件涉及科技产业动态，后续影响仍需结合更多来源验证")
    if title.startswith("媒体：") or title.startswith("媒体:"):
        return ensure_sentence_end(f"{title}，这是媒体视角下的公共议题观察，仍需结合事实来源和后续回应验证")

    if _category_code(item) == "hot":
        return ensure_sentence_end(f"{title}，{channel_name}已出现相关信息，后续仍需更多来源交叉验证")
    return ensure_sentence_end(f"{title}出现新进展，后续仍需结合更多来源持续验证")


def _should_rewrite_single_source_summary(item, sentence: str) -> bool:
    if _looks_like_noisy_sentence(sentence):
        return True
    title = item.title or ""
    if title.startswith("媒体：") or title.startswith("媒体:"):
        return True
    if any(marker in title for marker in PUBLIC_EVENT_MARKERS):
        return True
    return False


def _best_sentence(item) -> str:
    content = remove_title_prefix(item.content or "", item.title or "")
    if is_low_value_content(item.title or "", content):
        return ""
    sentences = split_sentences(content)
    meaningful_sentences = [sentence for sentence in sentences if not is_low_value_content(item.title or "", sentence)]
    if meaningful_sentences:
        return meaningful_sentences[0]
    if sentences:
        return sentences[0]
    fallback = content or item.title or ""
    if is_low_value_content(item.title or "", fallback):
        return ""
    return natural_clip(fallback, 120)


def _build_one_line(items) -> str:
    lead_item = items[0]
    entity = lead_item.core_entity or (lead_item.title or "")[:16]
    topic = _top_topic(items)
    keywords = _top_values(items, "tech_keywords", limit=2)
    count = _source_count(items)

    if _item_count(items) > 1:
        topic_phrase = f"{entity} 的{topic}" if topic else f"{entity} 相关事件"
        source_item_count = _item_count(items)
        heat_phrase = (
            f"讨论持续升温，已聚合 {source_item_count} 条来源内容，已出现多来源跟进"
            if source_item_count >= 4
            else "已出现多来源跟进"
        )
        if keywords:
            return ensure_sentence_end(f"{topic_phrase}{heat_phrase}，讨论集中在{'、'.join(keywords)}")
        return ensure_sentence_end(f"{topic_phrase}{heat_phrase}")

    sentence = _best_sentence(lead_item)
    title = lead_item.title or ""
    if not sentence:
        if title.startswith("媒体：") or title.startswith("媒体:") or any(marker in title for marker in PUBLIC_EVENT_MARKERS):
            rewritten = _title_based_event_summary(lead_item)
            if rewritten:
                return rewritten
        return ensure_sentence_end(f"{entity}正在形成热度线索，但当前缺少完整事实来源")
    if title.startswith("媒体：") or title.startswith("媒体:") or any(marker in title for marker in PUBLIC_EVENT_MARKERS):
        rewritten = _title_based_event_summary(lead_item)
        if rewritten:
            return rewritten
    if _should_rewrite_single_source_summary(lead_item, sentence):
        rewritten = _title_based_event_summary(lead_item)
        if rewritten:
            return rewritten
    if text_similarity(sentence, lead_item.title or "") >= 0.86:
        if keywords:
            return ensure_sentence_end(f"{entity}相关内容开始升温，核心讨论集中在{'、'.join(keywords)}")
        return ensure_sentence_end(f"{entity}相关内容开始升温，后续进展值得继续跟踪")
    return natural_clip(sentence, 120)


def _build_what_happened(items) -> str:
    lead = items[0]
    if is_low_value_content(lead.title or "", lead.content or ""):
        return "当前仍是热度线索，缺少完整事实来源支撑，暂不宜得出确定结论。"
    sentences = split_sentences(remove_title_prefix(lead.content or "", lead.title or ""))
    meaningful_sentences = [sentence for sentence in sentences if not is_low_value_content(lead.title or "", sentence)]
    summary = "".join(meaningful_sentences[:2]) if meaningful_sentences else _best_sentence(lead)
    keywords = _top_values(items, "tech_keywords", limit=2)
    if keywords and all(keyword not in summary for keyword in keywords):
        summary += f" 当前讨论还围绕{'、'.join(keywords)}展开。"
    return natural_clip(summary, 360)


def _build_why_it_matters(items) -> str:
    count = _source_count(items)
    entities = _top_values(items, "tech_entities", limit=2)
    keywords = _top_values(items, "tech_keywords", limit=2)
    if entities and keywords:
        return ensure_sentence_end(f"事件已覆盖{count}个来源，核心实体包括{'、'.join(entities)}，讨论重点落在{'、'.join(keywords)}，具备持续观察价值")
    if keywords:
        return ensure_sentence_end(f"事件已覆盖{count}个来源，讨论集中在{'、'.join(keywords)}，说明相关影响正在从单点信息扩散")
    return ensure_sentence_end(f"事件已覆盖{count}个来源，当前更适合结合后续来源持续验证其真实影响")


def _build_latest_update(chronological_items) -> str:
    latest = chronological_items[-1]
    latest_sentence = _best_sentence(latest)
    latest_keywords = _top_values([latest], "tech_keywords", limit=2)
    if len(chronological_items) == 1:
        return "当前暂无明确新增进展，事件仍在持续发酵。"
    first_sentence = _best_sentence(chronological_items[0])
    if text_similarity(first_sentence, latest_sentence) >= 0.86:
        if latest_keywords:
            return ensure_sentence_end(f"最新来源继续聚焦{'、'.join(latest_keywords)}，当前讨论仍围绕同一核心事实延伸")
        return "最新来源仍围绕同一核心事实展开，暂未形成明显新增进展。"
    if latest_keywords and all(keyword not in latest_sentence for keyword in latest_keywords):
        latest_sentence = f"{latest_sentence.rstrip('。！？!?')}，新增讨论重点包括{'、'.join(latest_keywords)}。"
    return natural_clip(latest_sentence, 220)


def _build_heat_reason(items) -> str:
    count = _source_count(items)
    topic = _top_topic(items)
    keywords = _top_values(items, "tech_keywords", limit=3)
    parts: list[str] = []
    if count > 1:
        parts.append(f"{count}个来源正在跟进")
    if topic:
        parts.append(f"属于{topic}类热点")
    if keywords:
        parts.append(f"关键词集中在{'、'.join(keywords)}")
    if not parts:
        parts.append("来源更新时间较新")
    return ensure_sentence_end("；".join(parts) + "，因此具备继续观察的热点价值")


def _build_risk_notice(items) -> str:
    profiles = [build_acquisition_quality_profile(item) for item in items]
    weak = sum(1 for profile in profiles if profile.needs_attention)
    incomplete = sum(1 for profile in profiles if profile.status in {"list_only", "failed", "pending"})
    risks: list[str] = []
    if weak:
        risks.append(f"{weak}条来源详情质量偏弱")
    if incomplete:
        risks.append(f"{incomplete}条来源仍需要详情补偿")
    if _source_count(items) <= 1:
        risks.append("当前只有单一来源")
    if not risks:
        return "当前来源完整度和交叉验证情况较好，暂未发现明显采集风险。"
    return ensure_sentence_end("；".join(risks) + "，分析结论需要结合后续采集持续校准")


def _build_source_compare(items) -> str:
    names: list[str] = []
    for item in items:
        name = item.channel.name if getattr(item, "channel", None) else ""
        if name and name not in names:
            names.append(name)
    if len(names) >= 2:
        return ensure_sentence_end(f"当前事件覆盖{'、'.join(names[:4])}等来源，可用于观察不同渠道的叙事差异")
    if names:
        return ensure_sentence_end(f"当前主要来自{names[0]}，还需要更多渠道补充交叉视角")
    return "当前来源渠道信息不足，暂时无法形成可靠的来源对比。"


def _confidence_text(items) -> tuple[str, float, float]:
    profiles = [build_acquisition_quality_profile(item) for item in items]
    count = _source_count(items)
    usable = sum(1 for profile in profiles if profile.usable)
    complete = sum(1 for profile in profiles if profile.status == "complete" and profile.usable)
    avg = round(sum(profile.completeness_score for profile in profiles) / max(len(profiles), 1))
    if count >= 3 and complete >= 2 and avg >= 70:
        level, confidence = "高", 0.86
    elif count >= 2 and usable >= 1:
        level, confidence = "中", 0.68
    else:
        level, confidence = "低", 0.45
    return f"分析可信度：{level}。当前平均完整度分为{avg}，来源数量为{count}。", confidence, float(avg)


def _facts(items) -> list[EventFact]:
    facts: list[EventFact] = []
    for item in items[:5]:
        sentence = _best_sentence(item)
        if sentence:
            facts.append(
                EventFact(
                    fact_type="core_fact",
                    content=sentence,
                    source_item_id=item.id,
                    confidence=0.72,
                    evidence={"title": item.title, "url": item.source_url},
                )
            )
    return facts


def _timeline(chronological_items) -> list[TimelinePoint]:
    points: list[TimelinePoint] = []
    for item in chronological_items:
        summary = _best_sentence(item)
        points.append(
            TimelinePoint(
                occurred_at=item.event_time or item.created_at,
                summary=natural_clip(summary, 140),
                source_item_id=item.id,
                confidence=0.72,
                evidence={"title": item.title, "url": item.source_url},
            )
        )
    return points


class RuleEventAnalysisProvider:
    provider = "rule"
    model_name = ""

    def analyze(self, items, chronological_items=None, history_context: str | None = None) -> EventAnalysisResult:
        if not items:
            raise ValueError("event analysis requires at least one source item")
        chronological_items = chronological_items or items
        confidence_text, confidence, quality_score = _confidence_text(items)

        # 收集使用的 Info ID 用于溯源
        used_info_ids = [item.id for item in items if item.id]

        # 生成历史上下文摘要
        generated_history_context = history_context or _build_history_context(items)

        return EventAnalysisResult(
            one_line_summary=_build_one_line(items),
            what_happened=_build_what_happened(items),
            why_it_matters=_build_why_it_matters(items),
            latest_update=_build_latest_update(chronological_items),
            heat_reason=_build_heat_reason(items),
            risk_notice=_build_risk_notice(items),
            source_compare=_build_source_compare(items),
            analysis_confidence=confidence_text,
            timeline_points=_timeline(chronological_items),
            facts=_facts(items),
            used_info_ids=used_info_ids,
            history_context=generated_history_context,
            provider=self.provider,
            model_name=self.model_name,
            mode="rule",
            quality_score=quality_score,
            confidence=confidence,
        )


def _build_history_context(items) -> str:
    """生成历史背景摘要（Rule模式使用）。"""
    if not items:
        return ""

    # 收集关键词和实体
    entities = _top_values(items, "tech_entities", limit=3)
    keywords = _top_values(items, "tech_keywords", limit=3)

    if not entities and not keywords:
        return ""

    parts = []
    if entities:
        parts.append(f"涉及实体包括{'、'.join(entities)}")
    if keywords:
        parts.append(f"讨论关键词包括{'、'.join(keywords)}")

    return "；".join(parts) + "。"
