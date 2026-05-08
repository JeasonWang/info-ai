from dataclasses import dataclass
import time
from typing import Protocol

from services.detail_pipeline import DetailPipelineResult, DetailStrategyResult, run_detail_pipeline


@dataclass
class DetailContext:
    """详情策略执行上下文，后续 HTTP、渲染和搜索补全策略共享这一份输入。"""

    title: str
    list_content: str
    source_url: str
    channel_code: str
    info_id: int | None = None
    last_failure_reason: str = ""
    strategy_hint: str = ""


class DetailStrategy(Protocol):
    """详情抓取策略接口；具体策略只负责抓取候选正文，不负责最终评分。"""

    name: str

    def fetch(self, context: DetailContext) -> DetailStrategyResult:
        """返回一个候选详情结果，质量判定交给 detail_pipeline。"""


class DetailStrategyChain:
    """按成本从低到高执行详情策略，并在拿到完整正文后短路。"""

    def __init__(self, strategies: list[DetailStrategy]):
        self.strategies = strategies
        self.execution_logs: list[dict] = []

    def run(self, context: DetailContext) -> DetailPipelineResult:
        candidates: list[DetailStrategyResult] = []
        best_result: DetailPipelineResult | None = None
        self.execution_logs = []

        for strategy in self.strategies:
            started_at = time.monotonic()
            try:
                candidate = strategy.fetch(context)
            except Exception as exc:
                candidate = DetailStrategyResult(
                    strategy=getattr(strategy, "name", strategy.__class__.__name__),
                    content="",
                    failure_reason=f"strategy_exception:{exc}",
                    matched_rules=["strategy_exception"],
                )
            elapsed_ms = int((time.monotonic() - started_at) * 1000)
            candidates.append(candidate)
            current = run_detail_pipeline(
                title=context.title,
                list_content=context.list_content,
                strategy_results=candidates,
                channel_code=context.channel_code,
            )
            self.execution_logs.append(
                {
                    "strategy": candidate.strategy,
                    "status": current.status,
                    "score": current.score,
                    "content_length": len(candidate.content or ""),
                    "failure_reason": current.failure_reason or candidate.failure_reason,
                    "elapsed_ms": elapsed_ms,
                }
            )
            if current.status == "complete":
                return current
            if best_result is None or current.score > best_result.score:
                best_result = current

        return run_detail_pipeline(
            title=context.title,
            list_content=context.list_content,
            strategy_results=candidates,
            channel_code=context.channel_code,
        )
