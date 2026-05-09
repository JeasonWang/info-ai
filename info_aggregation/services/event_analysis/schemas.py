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
    provider: str = "rule"
    model_name: str = ""
    mode: str = "rule"
    quality_score: float = 0.0
    confidence: float = 0.0
    fallback_used: bool = False
    failure_reason: str = ""
