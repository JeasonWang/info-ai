from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
import hashlib

from sqlalchemy import inspect

from database import (
    Event,
    EventAnalysisRun,
    EventAnalysisSnapshot,
    EventAnalysisSource,
    EventEvolution,
    EventFactSnapshot,
    EventItemLink,
    EventSummarySnapshot,
    EventTimelineAnalysis,
    EventTimelineEntry,
    Info,
    RebuildCheckpoint,
)
from services.collection.acquisition_quality import build_acquisition_quality_profile
from services.quality.data_quality import is_title_content_duplicate, normalize_text
from services.event_analysis import analyze_event_sources
from services.event_analysis.schemas import TimelinePoint
from services.analysis.event_display_quality import evaluate_event_display_quality


TECH_TOPIC_LABELS = {
    "chip_release": "芯片发布",
    "model_release": "模型发布",
    "dev_tool": "开发工具",
}


def _build_event_key(item: Info) -> tuple[int, str]:
    anchor = _event_anchor(item)
    return item.category_id, anchor


def _group_related_items(items: list[Info]) -> dict[tuple[int, str], list[Info]]:
    grouped_items: dict[tuple[int, str], list[Info]] = defaultdict(list)
    for item in items:
        grouped_items[_build_event_key(item)].append(item)
    return _merge_related_groups(grouped_items)


def _event_anchor(item: Info) -> str:
    """为事件聚合选择稳定锚点，优先使用实体字段，弱化标题措辞差异。"""

    for value in [item.core_entity, *_split_csv(item.tech_entities), *_split_csv(item.tech_keywords)]:
        normalized = _normalize_anchor(value)
        if normalized:
            return normalized

    title = normalize_text(item.title or "")
    title = _remove_event_action_words(title)
    return (title[:16] or normalize_text(item.title or "")[:16]).strip()


def _normalize_anchor(value: str) -> str:
    normalized = normalize_text(value)
    if len(normalized) < 2:
        return ""
    return normalized[:24]


def _remove_event_action_words(value: str) -> str:
    for word in ("发布", "宣布", "回应", "通报", "曝光", "上线", "热搜", "价格", "方案", "能力", "新进展", "新版本"):
        value = value.replace(word, "")
    return value.strip(" ，。:：-—_")


def _build_event_key_value(category_id: int, anchor: str) -> str:
    """生成事件稳定键，保证同一分类下同一核心实体重建时能命中同一事件。"""

    raw_key = f"{category_id}:{_normalize_summary_text(anchor).lower()}"
    return hashlib.sha1(raw_key.encode("utf-8")).hexdigest()


def _text_similarity(left: str, right: str) -> float:
    normalized_left = _normalize_summary_text(left)
    normalized_right = _normalize_summary_text(right)
    if not normalized_left or not normalized_right:
        return 0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def _event_terms(text: str) -> set[str]:
    normalized = _normalize_summary_text(text).lower()
    terms = set(_split_csv(normalized.replace("，", ",").replace("、", ",")))
    current = ""
    chunks: list[str] = []
    for char in normalized:
        if char.isspace() or char in "，。！？、；：,.!?;:/|()[]{}【】《》“”\"'":
            if current:
                chunks.append(current)
                current = ""
        else:
            current += char
    if current:
        chunks.append(current)
    for chunk in chunks:
        if chunk.isascii():
            if len(chunk) >= 2:
                terms.add(chunk)
            continue
        for index in range(max(0, len(chunk) - 1)):
            term = chunk[index : index + 2]
            if term not in {"事件", "热点", "最新", "关注", "相关", "进展", "网友", "消息", "视频"}:
                terms.add(term)
    return {term for term in terms if len(term) >= 2}


def _items_related(left: Info, right: Info) -> bool:
    left_text = f"{left.title or ''} {left.content or ''}"
    right_text = f"{right.title or ''} {right.content or ''}"
    if _text_similarity(left.title or "", right.title or "") >= 0.58:
        return True
    left_title_terms = _event_terms(left.title or "")
    right_title_terms = _event_terms(right.title or "")
    shared_title_terms = left_title_terms.intersection(right_title_terms)
    if not shared_title_terms:
        return False
    if len(shared_title_terms) < 2:
        return False
    left_terms = _event_terms(left_text)
    right_terms = _event_terms(right_text)
    shared_terms = left_terms.intersection(right_terms)
    if len(shared_terms) < 2:
        return False
    cue_words = ("事故", "通报", "坠", "伤", "死", "救援", "回应", "发布", "宣布", "价格", "模型", "芯片", "比赛")
    left_cue_hit = any(word in left_text for word in cue_words)
    right_cue_hit = any(word in right_text for word in cue_words)
    return left_cue_hit and right_cue_hit and len(shared_terms) >= 2


def _groups_related(left_items: list[Info], right_items: list[Info]) -> bool:
    for left in left_items[:3]:
        for right in right_items[:3]:
            if _items_related(left, right):
                return True
    return False


def _merge_related_groups(grouped_items: dict[tuple[int, str], list[Info]]) -> dict[tuple[int, str], list[Info]]:
    """保守合并同分类下相似标题组，补足无实体字段时的跨源聚合。"""

    merged: dict[tuple[int, str], list[Info]] = {}
    for key, items in grouped_items.items():
        target_key = None
        for existing_key, existing_items in merged.items():
            if existing_key[0] != key[0]:
                continue
            if key[1] == existing_key[1] or _groups_related(existing_items, items):
                target_key = existing_key
                break
        if target_key:
            merged[target_key].extend(items)
        else:
            merged[key] = list(items)
    return merged


def _is_low_quality_item(item: Info) -> bool:
    profile = build_acquisition_quality_profile(item)
    if profile.quality_level == "unusable":
        return True
    return is_title_content_duplicate(item.title or "", item.content or "")


def _quality_score(item: Info) -> float:
    profile = build_acquisition_quality_profile(item)
    content = _normalize_summary_text(item.content)
    status_bonus = {
        "complete": 45,
        "partial": 25,
        "list_only": 5,
        "failed": -40,
        "pending": 0,
    }.get(profile.status, 0)
    completeness = profile.completeness_score * 0.45
    value = profile.value_score * 0.35
    freshness = profile.freshness_score * 0.1
    duplicate_penalty = 35 if _text_similarity(item.title, content) >= 0.9 else 0
    return status_bonus + completeness + value + freshness - duplicate_penalty


def _event_item_sort_key(item: Info) -> tuple[float, object, int]:
    return (_quality_score(item), item.event_time or item.created_at, item.id)


def _prioritize_event_items(items: list[Info]) -> list[Info]:
    """事件分析优先使用高质量来源，避免短正文或列表摘要污染摘要结论。"""

    return sorted(items, key=_event_item_sort_key, reverse=True)


def _analysis_ready_items(items: list[Info]) -> list[Info]:
    ready_items = [
        item
        for item in _prioritize_event_items(items)
        if build_acquisition_quality_profile(item).usable and _quality_score(item) >= 45
    ]
    return ready_items or _prioritize_event_items(items)


def _split_csv(raw_value: str) -> list[str]:
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _collect_top_values(items: list[Info], attr_name: str, limit: int = 3) -> list[str]:
    counter: dict[str, int] = {}
    for item in items:
        raw_value = getattr(item, attr_name, "") or ""
        for value in _split_csv(raw_value):
            counter[value] = counter.get(value, 0) + 1
    return [value for value, _ in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def _collect_top_topic(items: list[Info]) -> str:
    counter: dict[str, int] = {}
    for item in items:
        if not item.tech_topic_type:
            continue
        counter[item.tech_topic_type] = counter.get(item.tech_topic_type, 0) + 1
    if not counter:
        return ""
    topic_type = sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return TECH_TOPIC_LABELS.get(topic_type, topic_type)


def _build_one_line(items: list[Info]) -> str:
    entity = items[0].core_entity or items[0].title[:12]
    topic_label = _collect_top_topic(items)
    source_count = len(items)
    topic_phrase = f"{entity} 的{topic_label}" if topic_label else f"{entity} 相关"

    if source_count <= 1:
        lead_content = _clip_summary_text(items[0].content, 120)
        title = _normalize_summary_text(items[0].title)
        if lead_content:
            if title and lead_content.startswith(title):
                lead_content = lead_content[len(title):].lstrip("，。,:：;； ")
            if lead_content:
                return lead_content
        return f"{topic_phrase}内容正在引发关注。"
    if source_count <= 3:
        return f"{topic_phrase}讨论正在升温，已出现多来源跟进。"
    return f"{topic_phrase}讨论持续升温，已聚合 {source_count} 条来源内容。"


def _build_what_happened(items: list[Info]) -> str:
    lead_item = items[0]
    lead_content = _clip_summary_text(lead_item.content, 360)
    top_keywords = _collect_top_values(items, "tech_keywords", limit=2)
    if lead_content and top_keywords:
        return f"{lead_content} 当前讨论主要围绕 {'、'.join(top_keywords)} 展开。"
    return lead_content or "暂时还没有提炼出事件摘要。"


def _build_why_it_matters(items: list[Info]) -> str:
    source_count = len({item.channel_id for item in items})
    top_entities = _collect_top_values(items, "tech_entities", limit=2)
    top_keywords = _collect_top_values(items, "tech_keywords", limit=2)

    if top_entities and top_keywords:
        return (
            f"这条事件已扩散到 {source_count} 个来源，讨论集中在 {'、'.join(top_entities)} "
            f"以及 {'、'.join(top_keywords)} 等技术点，说明它正在形成跨平台的持续影响。"
        )

    if top_entities:
        return f"这条事件已扩散到 {source_count} 个来源，且多个平台都在持续关注 {'、'.join(top_entities)}，说明它不再只是零散讨论。"

    return f"这条事件已扩散到 {source_count} 个来源，说明它不再只是单个平台的零散讨论。"


def _normalize_summary_text(text: str) -> str:
    return " ".join((text or "").split()).strip()


def _clip_summary_text(text: str, max_length: int) -> str:
    normalized = _normalize_summary_text(text)
    if len(normalized) <= max_length:
        return normalized
    clipped = normalized[:max_length]
    for delimiter in ("。", "！", "？", ".", "!", "?"):
        index = clipped.rfind(delimiter)
        if index >= max(40, int(max_length * 0.45)):
            return clipped[: index + 1].strip()
    return clipped.rstrip("，、；;：: ") + "..."


def _build_latest_update(items: list[Info]) -> str:
    latest_item = items[-1]
    lead_item = items[0]
    latest_content = _clip_summary_text(latest_item.content, 260)
    lead_content = _clip_summary_text(lead_item.content, 260)
    latest_keywords = _split_csv(latest_item.tech_keywords)

    # 如果事件首条和最新一条内容几乎一致，说明还没有提炼出真正的增量进展，
    # 这里返回更明确的状态语句，避免前端出现“重点结论”和“最新进展”完全重复。
    if not latest_content:
        return "当前暂无明确新增进展，事件仍在持续发酵。"

    if latest_content == lead_content:
        if len(items) > 1:
            if latest_keywords:
                return f"最新一轮更新继续聚焦 {'、'.join(latest_keywords[:2])}，当前讨论仍围绕同一核心事实延伸。"
            return f"最新一轮更新来自 {latest_item.title}，当前讨论仍围绕同一核心事实延伸。"
        return "当前暂无明确新增进展，事件仍在持续发酵。"

    if latest_keywords:
        return f"{latest_content} 当前新增讨论重点集中在 {'、'.join(latest_keywords[:2])}。"

    return latest_content


def _build_heat_reason(items: list[Info]) -> str:
    source_count = len({item.channel_id for item in items})
    topic_label = _collect_top_topic(items)
    top_entities = _collect_top_values(items, "tech_entities", limit=2)
    top_keywords = _collect_top_values(items, "tech_keywords", limit=2)

    reason_parts: list[str] = []
    if source_count > 1:
        reason_parts.append(f"已出现 {source_count} 个来源跟进")
    if topic_label:
        reason_parts.append(f"属于{topic_label}类热点")
    if top_entities:
        reason_parts.append(f"核心实体集中在 {'、'.join(top_entities)}")
    if top_keywords:
        reason_parts.append(f"讨论关键词包括 {'、'.join(top_keywords)}")

    if reason_parts:
        return "；".join(reason_parts) + "，因此具备继续观察的热点价值。"
    return "当前热度主要来自最新来源更新，仍需要更多来源交叉验证。"


def _build_risk_notice(items: list[Info]) -> str:
    profiles = [build_acquisition_quality_profile(item) for item in items]
    weak_count = sum(1 for profile in profiles if profile.needs_attention)
    list_only_count = sum(1 for profile in profiles if profile.status == "list_only")
    anti_crawl_count = sum(1 for profile in profiles if "anti_crawl_or_shell_page" in profile.risk_reasons)
    source_count = len({item.channel_id for item in items})

    risks: list[str] = []
    if weak_count:
        risks.append(f"{weak_count} 条来源详情质量偏弱")
    if list_only_count:
        risks.append(f"{list_only_count} 条仍停留在列表摘要")
    if anti_crawl_count:
        risks.append(f"{anti_crawl_count} 条疑似受登录或反爬影响")
    if source_count <= 1:
        risks.append("目前只有单一来源")

    if not risks:
        return "当前来源完整度和交叉验证情况较好，暂未发现明显采集风险。"
    return "；".join(risks) + "，分析结论需要随着后续补偿和新增来源持续校准。"


def _build_source_compare(items: list[Info]) -> str:
    channel_names = []
    for item in items:
        if item.channel and item.channel.name not in channel_names:
            channel_names.append(item.channel.name)
    if len(channel_names) >= 2:
        return f"当前事件覆盖 {'、'.join(channel_names[:4])} 等来源，可用于观察不同渠道的叙事差异。"
    if channel_names:
        return f"当前主要来自 {channel_names[0]}，还需要更多渠道补充交叉视角。"
    return "当前来源渠道信息不足，暂时无法形成可靠的来源对比。"


def _build_analysis_confidence(items: list[Info]) -> str:
    profiles = [build_acquisition_quality_profile(item) for item in items]
    source_count = len({item.channel_id for item in items})
    usable_count = sum(1 for profile in profiles if profile.usable)
    complete_count = sum(1 for profile in profiles if profile.status == "complete" and profile.usable)
    avg_completeness = round(sum(profile.completeness_score for profile in profiles) / max(len(profiles), 1))

    if source_count >= 3 and complete_count >= 2 and avg_completeness >= 70:
        level = "高"
        reason = "多来源交叉验证较充分，代表来源正文完整度较好"
    elif source_count >= 2 and usable_count >= 1:
        level = "中"
        reason = "已有可用来源支撑，但仍需要继续观察后续补充"
    else:
        level = "低"
        reason = "来源数量或详情完整度不足，当前更适合作为线索跟踪"

    return f"分析可信度：{level}。{reason}；当前平均完整度分为 {avg_completeness}。"


def _load_existing_events(session) -> dict[str, Event]:
    """按稳定键加载已有事件，用于重建时复用原事件ID。"""

    table_names = set(inspect(session.get_bind()).get_table_names())
    if "event" not in table_names:
        return {}
    columns = {column["name"] for column in inspect(session.get_bind()).get_columns("event")}
    if "event_key" not in columns:
        return {}
    return {event.event_key: event for event in session.query(Event).filter(Event.event_key != "").all()}


def _find_historical_events(core_entity: str, existing_events: list[Event]) -> list[Event]:
    """查找同实体的历史事件，按时间倒序排列。"""
    if not core_entity:
        return []
    normalized_entity = normalize_text(core_entity)
    historical = [
        e for e in existing_events
        if e.event_key and normalize_text(e.title or "")[:12] == normalized_entity[:12]
        or _text_similarity(e.title or "", core_entity) > 0.7
    ]
    return sorted(historical, key=lambda e: e.last_updated_at or e.created_at, reverse=True)


def _analyze_evolution(
    current_group: list[Info],
    previous_event: Event,
    session
) -> tuple[str, str, int]:
    """
    分析演变类型和关键变化。
    返回: (evolution_type, key_change, source_count_delta)
    """
    current_source_count = len(current_group)
    previous_source_count = previous_event.source_count or 0
    source_delta = current_source_count - previous_source_count

    # 分析演变类型
    evolution_type = "none"
    if source_delta > 3:
        evolution_type = "escalation"
    elif source_delta > 0:
        evolution_type = "expansion"
    elif source_delta < -3:
        evolution_type = "correction"

    # 检查是否反复出现
    if previous_event.event_generation and previous_event.event_generation >= 3:
        evolution_type = "recurrence"

    # 生成关键变化描述
    key_change = ""
    current_entities = set()
    for item in current_group:
        for entity in _split_csv(item.tech_entities or ""):
            current_entities.add(entity)

    if evolution_type == "escalation":
        key_change = f"来源数从 {previous_source_count} 增加到 {current_source_count}，事件持续升温"
    elif evolution_type == "expansion":
        key_change = f"新增 {source_delta} 个来源，影响范围扩大"
    elif evolution_type == "correction":
        key_change = f"来源数从 {previous_source_count} 减少到 {current_source_count}，可能存在信息修正"
    elif evolution_type == "recurrence":
        key_change = f"同类事件已出现 {previous_event.event_generation + 1} 次，呈现反复特征"

    return evolution_type, key_change, source_delta


def _query_historical_infos(core_entity: str, session, limit: int = 50) -> list[Info]:
    """查询历史信息（用于构建完整时间线）。"""
    if not core_entity:
        return []
    normalized_entity = normalize_text(core_entity)
    return (
        session.query(Info)
        .filter(
            Info.is_deleted == 0,
            Info.title.like(f"%{normalized_entity[:6]}%")
        )
        .order_by(Info.event_time.desc())
        .limit(limit)
        .all()
    )


def _build_full_timeline(historical_infos: list[Info], current_group: list[Info]) -> list[TimelinePoint]:
    """构建完整时间线（历史 + 当前）。"""
    from services.event_analysis.schemas import TimelinePoint

    timeline: list[TimelinePoint] = []

    # 添加历史信息
    for item in historical_infos[:20]:
        timeline.append(TimelinePoint(
            occurred_at=item.event_time or item.created_at,
            summary=_clip_summary_text(item.content, 100),
            source_item_id=item.id,
            confidence=0.5,
        ))

    # 添加当前信息（时间线更精确）
    for item in current_group:
        timeline.append(TimelinePoint(
            occurred_at=item.event_time or item.created_at,
            summary=_clip_summary_text(item.content, 100),
            source_item_id=item.id,
            confidence=0.8,
        ))

    # 按时间排序
    timeline.sort(key=lambda p: p.occurred_at, reverse=True)
    return timeline[:50]


def _generate_evolution_summary(
    evolution_type: str,
    current_group: list[Info],
    historical_events: list[Event]
) -> str:
    """生成演变摘要。"""
    if evolution_type == "none":
        return "本次分析未检测到显著的演变特征"

    summaries = {
        "escalation": "事件呈现明显升级趋势，来源数量大幅增加，需要重点关注",
        "expansion": "事件影响范围有所扩大，新增多个来源跟进",
        "correction": "事件信息可能存在修正，来源数量有所减少",
        "recurrence": "同类事件反复出现，表明这是一个持续性热点话题",
    }
    return summaries.get(evolution_type, "")


def _determine_evolution_stage(
    current_group: list[Info],
    historical_events: list[Event],
    source_count_delta: int = 0
) -> str:
    """确定演变阶段。"""
    # 首次出现
    if not historical_events:
        return "emerging"

    generation = historical_events[0].event_generation + 1 if historical_events else 1

    # 反复出现
    if generation > 3:
        return "recurring"

    # 检查关键词判断是否终结
    for item in current_group:
        content = (item.content or "").lower()
        if any(kw in content for kw in ["结束", "解决", "已定", "闭幕", "完成", "终结"]):
            return "resolved"

    # 检查热度峰值
    if len(current_group) > 5:
        return "peak"

    # 检查是否升温/升级
    if source_count_delta > 3:
        return "escalating"

    # 检查是否扩大
    channel_count = len({item.channel_id for item in current_group})
    if channel_count > 5:
        return "expanding"

    # 检查是否消退
    if source_count_delta < 0 and generation > 1:
        return "declining"

    return "emerging"


def _build_history_context(core_entity: str, historical_events: list[Event]) -> str:
    """把历史事件压缩成分析可消费的短上下文。"""
    if not historical_events:
        return ""

    event_summaries = []
    for event in historical_events[:3]:
        updated_at = event.last_updated_at.strftime("%Y-%m-%d") if event.last_updated_at else ""
        event_summaries.append(f"{updated_at} {event.title}（第{event.event_generation or 1}代，来源{event.source_count or 0}条）")

    entity = core_entity or "该主题"
    return f"{entity} 此前已有相关事件：" + "；".join(event_summaries)


def _build_history_context_for_event(event: Event) -> str:
    """为已有事件的增量分析构造历史上下文。"""
    if not event:
        return ""
    parts = [f"当前事件已聚合 {event.source_count or 0} 条来源"]
    if event.event_generation and event.event_generation > 1:
        parts.append(f"这是同类事件第 {event.event_generation} 代")
    if event.evolution_stage:
        parts.append(f"当前演变阶段为 {event.evolution_stage}")
    if event.title:
        parts.append(f"事件标题：{event.title}")
    return "；".join(parts) + "。"


def _replace_event_analysis_outputs(session, event: Event, analysis, analysis_group: list[Info]) -> EventAnalysisRun:
    """
    写入一次新的分析运行，并刷新当前展示用快照。

    历史运行和 EventAnalysisSource 会保留；摘要、时间线和当前分析快照只保留最新版本，
    避免事件详情页读到旧输出。
    """
    now = datetime.now()
    analysis_run = EventAnalysisRun(
        event_id=event.id,
        analysis_version="v1",
        mode=analysis.mode,
        provider=analysis.provider,
        model_name=analysis.model_name,
        status="succeeded" if not analysis.failure_reason else "fallback",
        input_item_count=len(analysis_group),
        quality_score=analysis.quality_score,
        confidence=analysis.confidence,
        fallback_used=1 if analysis.fallback_used else 0,
        failure_reason=analysis.failure_reason,
        started_at=now,
        finished_at=now,
    )
    session.add(analysis_run)
    session.flush()

    for index, item in enumerate(analysis_group, start=1):
        session.add(
            EventAnalysisSource(
                run_id=analysis_run.id,
                info_id=item.id,
                info_title=item.title[:200] if item.title else "",
                role="primary" if index == 1 else "media",
                weight=max(10, min(100, int(_quality_score(item)))),
                quality_score=int(_quality_score(item)),
            )
        )

    session.query(EventSummarySnapshot).filter(EventSummarySnapshot.event_id == event.id).delete()
    session.query(EventTimelineEntry).filter(EventTimelineEntry.event_id == event.id).delete()
    session.query(EventTimelineAnalysis).filter(EventTimelineAnalysis.event_id == event.id).delete()
    session.query(EventAnalysisSnapshot).filter(EventAnalysisSnapshot.event_id == event.id).delete()
    session.query(EventFactSnapshot).filter(EventFactSnapshot.event_id == event.id).delete()

    summary_values = [
        ("one_line", analysis.one_line_summary),
        ("what_happened", analysis.what_happened),
        ("why_it_matters", analysis.why_it_matters),
        ("latest_update", analysis.latest_update),
        ("heat_reason", analysis.heat_reason),
        ("risk_notice", analysis.risk_notice),
        ("source_compare", analysis.source_compare),
        ("analysis_confidence", analysis.analysis_confidence),
    ]
    session.add_all(
        [
            EventSummarySnapshot(event_id=event.id, summary_type=summary_type, content=content, version=1)
            for summary_type, content in summary_values
        ]
    )

    for analysis_type, content in summary_values:
        session.add(
            EventAnalysisSnapshot(
                event_id=event.id,
                run_id=analysis_run.id,
                analysis_type=analysis_type,
                content=content,
                provider=analysis.provider,
                model_name=analysis.model_name,
                quality_score=analysis.quality_score,
                confidence=analysis.confidence,
                version=1,
            )
        )

    for fact in analysis.facts:
        session.add(
            EventFactSnapshot(
                event_id=event.id,
                run_id=analysis_run.id,
                fact_type=fact.fact_type,
                content=fact.content,
                source_item_id=fact.source_item_id,
                confidence=fact.confidence,
                evidence=fact.evidence,
            )
        )

    for index, point in enumerate(analysis.timeline_points, start=1):
        session.add(
            EventTimelineEntry(
                event_id=event.id,
                run_id=analysis_run.id,
                occurred_at=point.occurred_at,
                summary=point.summary,
                source_item_id=point.source_item_id,
                confidence=point.confidence,
                evidence=point.evidence,
                display_order=index,
            )
        )
        session.add(
            EventTimelineAnalysis(
                event_id=event.id,
                run_id=analysis_run.id,
                occurred_at=point.occurred_at,
                summary=point.summary,
                source_item_id=point.source_item_id,
                confidence=point.confidence,
                evidence=point.evidence,
                display_order=index,
            )
        )

    return analysis_run


def _apply_display_quality(event: Event, items: list[Info], analysis=None) -> None:
    quality = evaluate_event_display_quality(items, analysis_quality_score=getattr(analysis, "quality_score", 0.0))
    event.status = quality.status
    event.display_quality_score = quality.score
    event.display_quality_level = quality.level
    event.display_quality_reason = quality.reason_text


def rebuild_events(session, limit: int = 200, mode: str = "incremental"):
    """
    重建事件。
    mode: "incremental" → 只处理新增Info，增量追加到现有事件
          "full"         → 全量重建（清除后重建）
    """
    if mode == "full":
        _full_rebuild(session, limit)
    else:
        _incremental_rebuild(session, limit)


def _get_latest_checkpoint(session) -> RebuildCheckpoint | None:
    """获取最新的检查点。"""
    return (
        session.query(RebuildCheckpoint)
        .order_by(RebuildCheckpoint.created_at.desc())
        .first()
    )


def _incremental_rebuild(session, limit: int = 200):
    """增量重建：只处理新增Info。"""
    rebuild_started_at = datetime.now()

    # 1. 获取检查点
    checkpoint = _get_latest_checkpoint(session)
    if checkpoint:
        max_info_id = checkpoint.max_info_id_processed
    else:
        max_info_id = (
            session.query(EventItemLink.item_id)
            .order_by(EventItemLink.item_id.desc())
            .limit(1)
            .scalar()
            or 0
        )

    # 2. 查询增量 Info。首次构建以最新窗口为基线，后续按检查点只处理新 ID。
    query = session.query(Info).filter(Info.is_deleted == 0)
    if checkpoint or max_info_id:
        new_infos = query.filter(Info.id > max_info_id).order_by(Info.id.asc()).limit(limit).all()
    else:
        new_infos = (
            query.order_by(Info.event_time.desc(), Info.created_at.desc(), Info.id.desc())
            .limit(limit)
            .all()
        )

    if not new_infos:
        return

    # 3. 加载现有事件
    existing_events = _load_existing_events(session)
    events_created = 0
    events_updated = 0
    max_processed_id = max_info_id

    # 4. 对每个新 Info 进行事件归属
    candidate_items = []
    for item in new_infos:
        if _is_low_quality_item(item):
            continue
        candidate_items.append(item)
        if item.id > max_processed_id:
            max_processed_id = item.id
    grouped_items = _group_related_items(candidate_items)

    for (category_id, anchor), group in grouped_items.items():
        event_key = _build_event_key_value(category_id, anchor)
        existing_event = existing_events.get(event_key)

        if existing_event:
            # 增量追加：更新现有事件
            if _incrementally_update_event(session, existing_event, group):
                events_updated += 1
        else:
            # 新建事件
            _create_new_event(session, group, event_key, existing_events)
            events_created += 1

    session.add(
        RebuildCheckpoint(
            checkpoint_type="incremental",
            max_info_id_processed=max_processed_id,
            items_processed=len(new_infos),
            events_created=events_created,
            events_updated=events_updated,
            started_at=rebuild_started_at,
            finished_at=datetime.now(),
        )
    )

    session.commit()


def _reanalyze_event_items(session, event: Event, all_event_items: list[Info]) -> bool:
    """基于给定来源重新生成分析输出；外部大模型调用完成后才写分析表。"""
    if not all_event_items:
        return False

    chronological_group = sorted(all_event_items, key=lambda item: item.event_time or item.created_at)
    prioritized_group = _prioritize_event_items(all_event_items)
    analysis_group = _analysis_ready_items(all_event_items)
    latest_item = chronological_group[-1]
    event.source_count = len(prioritized_group)
    if latest_item.event_time and latest_item.event_time > (event.last_updated_at or datetime.min):
        event.last_updated_at = latest_item.event_time
    analysis = analyze_event_sources(
        analysis_group,
        chronological_group,
        session=session,
        history_context=_build_history_context_for_event(event),
    )
    event.one_line_summary = analysis.one_line_summary
    _apply_display_quality(event, prioritized_group, analysis)
    _replace_event_analysis_outputs(session, event, analysis, analysis_group)
    return True


def _reanalyze_existing_event(session, event: Event) -> bool:
    """基于事件当前所有来源重新生成分析输出，不修改来源关联。"""
    all_event_items = (
        session.query(Info)
        .join(EventItemLink, EventItemLink.item_id == Info.id)
        .filter(EventItemLink.event_id == event.id)
        .all()
    )
    return _reanalyze_event_items(session, event, all_event_items)


def _incrementally_update_event(session, event: Event, new_group: list[Info]) -> bool:
    """增量更新现有事件：追加ItemLink，更新时间线/摘要。"""
    existing_item_ids = {
        item_id
        for (item_id,) in session.query(EventItemLink.item_id).filter(EventItemLink.event_id == event.id).all()
    }
    existing_event_items = (
        session.query(Info)
        .join(EventItemLink, EventItemLink.item_id == Info.id)
        .filter(EventItemLink.event_id == event.id)
        .all()
    )
    new_group = [item for item in new_group if item.id not in existing_item_ids]
    if not new_group:
        return False

    if not _reanalyze_event_items(session, event, existing_event_items + new_group):
        return False

    prioritized_group = _prioritize_event_items(new_group)

    # 添加新的ItemLink
    existing_link_count = (
        session.query(EventItemLink)
        .filter(EventItemLink.event_id == event.id)
        .count()
    )
    for index, item in enumerate(prioritized_group, start=existing_link_count + 1):
        session.add(
            EventItemLink(
                event_id=event.id,
                item_id=item.id,
                role="primary" if index == 1 else "media",
                is_primary=1 if index == 1 else 0,
                weight=max(10, min(100, int(_quality_score(item)))),
            )
        )

    return True


def _create_new_event(session, group: list[Info], event_key: str, existing_events: dict):
    """创建新事件。"""
    chronological_group = sorted(group, key=lambda item: item.event_time or item.created_at)
    prioritized_group = _prioritize_event_items(group)
    analysis_group = _analysis_ready_items(group)
    lead_item = analysis_group[0]
    latest_item = chronological_group[-1]

    event = Event(event_key=event_key)

    # 历史脉络分析
    core_entity = lead_item.core_entity or lead_item.title[:12]
    historical_events = _find_historical_events(core_entity, list(existing_events.values()))

    if historical_events:
        previous_event = historical_events[0]
        evolution_type, key_change, source_delta = _analyze_evolution(group, previous_event, session)
        evolution_summary = _generate_evolution_summary(evolution_type, group, historical_events)
        evolution_stage = _determine_evolution_stage(group, historical_events, source_delta)

        event.previous_event_id = previous_event.id
        event.event_generation = (previous_event.event_generation or 1) + 1
        event.evolution_stage = evolution_stage
    else:
        event.event_generation = 1
        event.evolution_stage = "emerging"

    history_context = _build_history_context(core_entity, historical_events)
    analysis = analyze_event_sources(analysis_group, chronological_group, session=session, history_context=history_context)

    event.title = lead_item.title
    event.one_line_summary = analysis.one_line_summary
    event.primary_category_id = lead_item.category_id
    _apply_display_quality(event, prioritized_group, analysis)
    event.heat_score = min(100, 60 + len(prioritized_group) * 10)
    event.freshness_score = 90
    event.composite_score = min(100, 70 + len(prioritized_group) * 8)
    event.source_count = len(prioritized_group)
    event.started_at = chronological_group[0].event_time or chronological_group[0].created_at
    event.last_updated_at = latest_item.event_time or latest_item.created_at

    session.add(event)
    session.flush()

    # 写入演变记录
    if event.previous_event_id:
        session.add(EventEvolution(
            event_id=event.id,
            previous_event_id=event.previous_event_id,
            evolution_type=evolution_type if 'evolution_type' in dir() else "none",
            evolution_summary=evolution_summary if 'evolution_summary' in dir() else "",
            source_count_delta=source_delta if 'source_delta' in dir() else 0,
            key_change=key_change if 'key_change' in dir() else "",
        ))

    _replace_event_analysis_outputs(session, event, analysis, analysis_group)

    # 写入ItemLink
    for index, item in enumerate(prioritized_group, start=1):
        session.add(
            EventItemLink(
                event_id=event.id,
                item_id=item.id,
                role="primary" if index == 1 else "media",
                is_primary=1 if index == 1 else 0,
                weight=max(10, min(100, int(_quality_score(item)))),
            )
        )

    # 更新existing_events
    existing_events[event_key] = event


def _full_rebuild(session, limit: int = 200):
    """全量重建：清除后重建所有事件。"""
    items = (
        session.query(Info)
        .filter(Info.is_deleted == 0)
        .order_by(Info.event_time.desc(), Info.created_at.desc(), Info.id.desc())
        .limit(limit)
        .all()
    )

    grouped_items = _group_related_items([item for item in items if not _is_low_quality_item(item)])

    existing_events = _load_existing_events(session)
    analysis_plans = []

    for (category_id, anchor), group in grouped_items.items():
        chronological_group = sorted(group, key=lambda item: item.event_time or item.created_at)
        prioritized_group = _prioritize_event_items(group)
        analysis_group = _analysis_ready_items(group)
        lead_item = analysis_group[0]
        latest_item = chronological_group[-1]
        event_key = _build_event_key_value(category_id, anchor)
        event = existing_events.get(event_key) or Event(event_key=event_key)

        # 历史脉络分析
        core_entity = lead_item.core_entity or lead_item.title[:12]
        historical_events = _find_historical_events(core_entity, list(existing_events.values()))

        if historical_events:
            previous_event = historical_events[0]
            evolution_type, key_change, source_delta = _analyze_evolution(group, previous_event, session)
            evolution_summary = _generate_evolution_summary(evolution_type, group, historical_events)
            evolution_stage = _determine_evolution_stage(group, historical_events, source_delta)

            # 保存演变分析结果，稍后在事件flush后写入
            pending_evolution = {
                "previous_event_id": previous_event.id,
                "event_generation": (previous_event.event_generation or 1) + 1,
                "evolution_stage": evolution_stage,
                "evolution_type": evolution_type,
                "evolution_summary": evolution_summary,
                "source_count_delta": source_delta,
                "key_change": key_change,
            }
        else:
            pending_evolution = None

        history_context = _build_history_context(core_entity, historical_events)
        analysis = analyze_event_sources(analysis_group, chronological_group, session=session, history_context=history_context)

        analysis_plans.append(
            {
                "analysis": analysis,
                "analysis_group": analysis_group,
                "chronological_group": chronological_group,
                "event": event,
                "event_key": event_key,
                "lead_item": lead_item,
                "latest_item": latest_item,
                "pending_evolution": pending_evolution,
                "prioritized_group": prioritized_group,
            }
        )

    session.query(EventItemLink).delete()
    session.query(EventTimelineEntry).delete()
    session.query(EventSummarySnapshot).delete()
    session.query(EventTimelineAnalysis).delete()
    session.query(EventAnalysisSnapshot).delete()
    session.query(EventFactSnapshot).delete()
    session.query(EventAnalysisSource).delete()
    session.query(EventAnalysisRun).delete()
    session.query(Event).update({Event.status: "archived"}, synchronize_session="fetch")

    for plan in analysis_plans:
        analysis = plan["analysis"]
        analysis_group = plan["analysis_group"]
        chronological_group = plan["chronological_group"]
        event = plan["event"]
        event_key = plan["event_key"]
        lead_item = plan["lead_item"]
        latest_item = plan["latest_item"]
        pending_evolution = plan["pending_evolution"]
        prioritized_group = plan["prioritized_group"]

        if pending_evolution:
            event.previous_event_id = pending_evolution["previous_event_id"]
            event.event_generation = pending_evolution["event_generation"]
            event.evolution_stage = pending_evolution["evolution_stage"]
        else:
            event.previous_event_id = None
            event.event_generation = 1
            event.evolution_stage = "emerging"

        event.title = lead_item.title
        event.one_line_summary = analysis.one_line_summary
        event.primary_category_id = lead_item.category_id
        _apply_display_quality(event, prioritized_group, analysis)
        event.heat_score = min(100, 60 + len(prioritized_group) * 10)
        event.freshness_score = 90
        event.composite_score = min(100, 70 + len(prioritized_group) * 8)
        event.source_count = len(prioritized_group)
        event.started_at = chronological_group[0].event_time or chronological_group[0].created_at
        event.last_updated_at = latest_item.event_time or latest_item.created_at
        event.event_key = event_key
        if event.id is None:
            session.add(event)
        session.flush()

        # 写入演变记录（事件flush后）
        if pending_evolution:
            session.add(EventEvolution(
                event_id=event.id,
                previous_event_id=pending_evolution["previous_event_id"],
                evolution_type=pending_evolution["evolution_type"],
                evolution_summary=pending_evolution["evolution_summary"],
                source_count_delta=pending_evolution["source_count_delta"],
                key_change=pending_evolution["key_change"],
            ))

        for index, item in enumerate(prioritized_group, start=1):
            session.add(
                EventItemLink(
                    event_id=event.id,
                    item_id=item.id,
                    role="primary" if index == 1 else "media",
                    is_primary=1 if index == 1 else 0,
                    weight=max(10, min(100, int(_quality_score(item)))),
                )
            )
        _replace_event_analysis_outputs(session, event, analysis, analysis_group)

    session.commit()
