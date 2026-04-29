from dataclasses import dataclass
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


class DetailStrategy(Protocol):
    """详情抓取策略接口；具体策略只负责抓取候选正文，不负责最终评分。"""

    name: str

    def fetch(self, context: DetailContext) -> DetailStrategyResult:
        """返回一个候选详情结果，质量判定交给 detail_pipeline。"""


class DetailStrategyChain:
    """按成本从低到高执行详情策略，并在拿到完整正文后短路。"""

    def __init__(self, strategies: list[DetailStrategy]):
        self.strategies = strategies

    def run(self, context: DetailContext) -> DetailPipelineResult:
        candidates: list[DetailStrategyResult] = []
        best_result: DetailPipelineResult | None = None

        for strategy in self.strategies:
            candidate = strategy.fetch(context)
            candidates.append(candidate)
            current = run_detail_pipeline(
                title=context.title,
                list_content=context.list_content,
                strategy_results=candidates,
            )
            if current.status == "complete":
                return current
            if best_result is None or current.score > best_result.score:
                best_result = current

        return run_detail_pipeline(
            title=context.title,
            list_content=context.list_content,
            strategy_results=candidates,
        )
