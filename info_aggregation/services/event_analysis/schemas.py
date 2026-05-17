from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EventFact:
    fact_type: str
    content: str
    source_item_id: int | None = None
    confidence: float = 0.0
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class TimelinePoint:
    occurred_at: datetime
    summary: str
    source_item_id: int | None = None
    confidence: float = 0.0
    evidence: dict[str, Any] = field(default_factory=dict)
    # New fields for enhanced timeline
    stage_label: str = ""
    merged_count: int = 1
    source_channels: list[str] = field(default_factory=list)


@dataclass
class EventTimeline:
    nodes: list[TimelinePoint] = field(default_factory=list)
    total_items: int = 0
    time_span_hours: float = 0.0
    stage_summary: str = ""


@dataclass
class EventAnalysisResult:
    one_line_summary: str
    what_happened: str
    why_it_matters: str
    latest_update: str
    heat_reason: str
    risk_notice: str
    source_compare: str
    analysis_confidence: str
    timeline_points: list[TimelinePoint]
    facts: list[EventFact] = field(default_factory=list)
    used_info_ids: list[int] = field(default_factory=list)
    # 历史脉络字段
    previous_event_id: int | None = None
    evolution_stage: str = "emerging"
    evolution_summary: str = ""
    full_timeline: list[TimelinePoint] = field(default_factory=list)
    history_context: str = ""
    provider: str = "rule"
    model_name: str = ""
    mode: str = "rule"
    quality_score: float = 0.0
    confidence: float = 0.0
    fallback_used: bool = False
    failure_reason: str = ""
