from dataclasses import dataclass


@dataclass(frozen=True)
class EventAnalysisTask:
    code: str
    name: str
    target_field: str
    instruction: str


DEFAULT_EVENT_ANALYSIS_TASKS = (
    EventAnalysisTask(
        code="summary",
        name="一句话判断",
        target_field="one_line_summary",
        instruction="生成35-90个中文字符的完整判断句，避免标题复读、半截话和无事实支撑的夸张表达。",
    ),
    EventAnalysisTask(
        code="fact_check",
        name="事实校验",
        target_field="risk_notice",
        instruction="核对事实是否被多来源支撑，识别单源、传言、营销号、缺少权威来源等风险，并写清仍需核实的内容。",
    ),
    EventAnalysisTask(
        code="source_compare",
        name="多源叙事差异",
        target_field="source_compare",
        instruction="比较不同渠道的关注点、立场和信息增量，指出哪些是确认事实，哪些只是评论或情绪表达。",
    ),
    EventAnalysisTask(
        code="history_relation",
        name="历史关联判断",
        target_field="evolution_summary",
        instruction="结合历史背景判断事件是首次出现、延续、升级、反转还是降温，并说明与历史事件的关系。",
    ),
)


def default_event_analysis_tasks() -> list[EventAnalysisTask]:
    return list(DEFAULT_EVENT_ANALYSIS_TASKS)


def normalize_event_analysis_tasks(tasks=None) -> list[EventAnalysisTask]:
    if tasks is None:
        return default_event_analysis_tasks()
    return [task for task in tasks if isinstance(task, EventAnalysisTask)]
