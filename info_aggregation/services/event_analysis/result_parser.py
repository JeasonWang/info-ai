from .schemas import EventAnalysisResult, TimelinePoint
from .text_utils import natural_clip


class EventAnalysisResultParser:
    """Convert LLM JSON into the internal event-analysis schema."""

    def parse(
        self,
        data: dict,
        chronological_items,
        provider: str,
        model_name: str,
    ) -> EventAnalysisResult:
        timeline_points = [
            TimelinePoint(
                occurred_at=item.event_time or item.created_at,
                summary=natural_clip(item.content or item.title or "", 140),
                source_item_id=item.id,
                confidence=0.7,
                evidence={"title": item.title, "url": item.source_url},
            )
            for item in chronological_items
        ]
        return EventAnalysisResult(
            one_line_summary=str(data.get("one_line_summary", "")),
            what_happened=str(data.get("what_happened", "")),
            why_it_matters=str(data.get("why_it_matters", "")),
            latest_update=str(data.get("latest_update", "")),
            heat_reason=str(data.get("heat_reason", "")),
            risk_notice=str(data.get("risk_notice", "")),
            source_compare=str(data.get("source_compare", "")),
            analysis_confidence=str(data.get("analysis_confidence", "")),
            evolution_summary=str(data.get("evolution_summary", "")),
            history_context=str(data.get("history_context", "")),
            timeline_points=timeline_points,
            used_info_ids=[item.id for item in chronological_items if item.id],
            provider=provider,
            model_name=model_name,
            mode="llm",
            quality_score=80.0,
            confidence=0.78,
        )
