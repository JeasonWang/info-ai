"""Timeline builder: merge, deduplicate, and annotate event timelines."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class TimelineNode:
    """A single timeline node, possibly merging multiple info items."""
    occurred_at: datetime
    summary: str
    source_item_ids: list[int] = field(default_factory=list)
    source_channels: list[str] = field(default_factory=list)
    merged_count: int = 1
    confidence: float = 0.72
    evidence: dict[str, Any] = field(default_factory=dict)
    stage_label: str = ""  # "发酵" / "扩散" / "反转" / "降温"


@dataclass
class EventTimeline:
    """Complete timeline for a single event."""
    nodes: list[TimelineNode] = field(default_factory=list)
    total_items: int = 0
    time_span_hours: float = 0.0
    stage_summary: str = ""  # LLM-generated stage summary placeholder


def _channel_name(item) -> str:
    return item.channel.name if getattr(item, "channel", None) else ""


def _channel_code(item) -> str:
    return item.channel.code if getattr(item, "channel", None) else ""


def _best_sentence(item) -> str:
    """Extract the most informative sentence from item content."""
    from .text_utils import clean_source_text, split_sentences, _looks_like_noisy_sentence
    content = clean_source_text(item.content or "")
    title = clean_source_text(item.title or "")
    sentences = split_sentences(content)
    
    # Remove title-like sentences and noisy ones
    candidates = [s for s in sentences if s != title and not _looks_like_noisy_sentence(s)]
    if not candidates:
        candidates = sentences
    
    if not candidates:
        # Fallback to title
        return title[:140] if title else ""
    
    # Pick the sentence with highest information density (longest meaningful one)
    return max(candidates, key=lambda s: len(s))[:140]


def _merge_window(
    items, window_minutes: int = 60
) -> list[list]:
    """Group items into time windows."""
    if not items:
        return []
    
    sorted_items = sorted(items, key=lambda x: x.event_time or x.created_at)
    windows: list[list] = [[sorted_items[0]]]
    
    for item in sorted_items[1:]:
        current_time = item.event_time or item.created_at
        window_start = windows[-1][0].event_time or windows[-1][0].created_at
        
        if (current_time - window_start) <= timedelta(minutes=window_minutes):
            windows[-1].append(item)
        else:
            windows.append([item])
    
    return windows


def _infer_stage_label(
    node_index: int,
    total_nodes: int,
    node: TimelineNode,
    all_nodes: list[TimelineNode],
) -> str:
    """Infer stage label based on position and context."""
    if total_nodes <= 1:
        return "发酵"
    
    position_ratio = node_index / max(total_nodes - 1, 1)
    
    # Check if this node introduces new info vs confirming previous
    if node_index == 0:
        return "发酵"
    
    # If there's a significant time gap after this node, might be a turning point
    if node_index < total_nodes - 1:
        next_node = all_nodes[node_index + 1]
        gap_hours = (next_node.occurred_at - node.occurred_at).total_seconds() / 3600
        if gap_hours > 24 and position_ratio > 0.5:
            return "降温"
    
    if position_ratio <= 0.3:
        return "扩散"
    elif position_ratio <= 0.7:
        return "扩散"  # Could be "反转" if sentiment changes detected
    else:
        return "降温"
    
    return "扩散"


def build_timeline(
    items,
    chronological_items=None,
    evolution_stage: str | None = None,
    window_minutes: int = 60,
) -> EventTimeline:
    """
    Build a polished timeline from raw info items.
    
    Args:
        items: source items for this event
        chronological_items: items sorted by time (defaults to items)
        evolution_stage: current evolution stage from event_evolution table
        window_minutes: time window for merging nodes
    """
    chronological_items = chronological_items or items
    if not chronological_items:
        return EventTimeline()
    
    # Merge nearby items into windows
    windows = _merge_window(chronological_items, window_minutes)
    
    nodes: list[TimelineNode] = []
    for window_items in windows:
        # Pick the item with highest detail_score as representative
        best = max(window_items, key=lambda x: getattr(x, "detail_score", 0) or 0)
        summary = _best_sentence(best)
        
        # Collect all channels in this window
        channels = list({_channel_name(item) for item in window_items})
        channel_codes = list({_channel_code(item) for item in window_items})
        
        # Collect all source IDs
        source_ids = [item.id for item in window_items if item.id]
        
        node = TimelineNode(
            occurred_at=best.event_time or best.created_at,
            summary=summary,
            source_item_ids=source_ids,
            source_channels=channels,
            merged_count=len(window_items),
            confidence=max(0.6, min(0.95, 0.6 + len(window_items) * 0.1)),
            evidence={
                "title": best.title,
                "url": best.source_url,
                "channel_codes": channel_codes,
            },
        )
        nodes.append(node)
    
    # Annotate stages
    for i, node in enumerate(nodes):
        node.stage_label = _infer_stage_label(i, len(nodes), node, nodes)
    
    # Calculate time span
    if nodes:
        span = (nodes[-1].occurred_at - nodes[0].occurred_at).total_seconds() / 3600
    else:
        span = 0.0
    
    # Generate a brief stage summary (rule-based, LLM enhancement later)
    stage_summary = _build_stage_summary(nodes, evolution_stage)
    
    return EventTimeline(
        nodes=nodes,
        total_items=len(chronological_items),
        time_span_hours=round(span, 1),
        stage_summary=stage_summary,
    )


def _build_stage_summary(nodes: list[TimelineNode], evolution_stage: str | None) -> str:
    """Build a one-line narrative trajectory summary from the timeline nodes."""
    if not nodes:
        return ""
    
    stage_groups: dict[str, list[TimelineNode]] = {}
    for node in nodes:
        stage_groups.setdefault(node.stage_label, []).append(node)
    
    # Build narrative trajectory phrases in chronological stage order
    stage_narrative = {
        "发酵": "曝光发酵",
        "扩散": "经多方报道扩散",
        "反转": "出现情节反转",
        "降温": "进入降温阶段",
    }
    stage_order = ["发酵", "扩散", "反转", "降温"]
    trajectory_parts: list[str] = []
    for stage in stage_order:
        if stage in stage_groups:
            trajectory_parts.append(stage_narrative[stage])
    
    if evolution_stage:
        stage_map = {
            "emerging": "处于发酵期",
            "peak": "持续发酵中",
            "declining": "关注度已下降",
            "resolved": "已有明确结论",
            "recurring": "再次升温",
        }
        current = stage_map.get(evolution_stage, evolution_stage)
        trajectory = "，".join(trajectory_parts) if trajectory_parts else ""
        if trajectory:
            return f"事件从{trajectory}，目前{current}。"
        return f"事件目前{current}。"
    
    if not trajectory_parts:
        return ""
    if len(trajectory_parts) == 1:
        return f"事件处于{trajectory_parts[0]}阶段。"
    last = trajectory_parts[-1]
    rest = "，".join(trajectory_parts[:-1])
    return f"事件从{rest}，目前已{last}。"
