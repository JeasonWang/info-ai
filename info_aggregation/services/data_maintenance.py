"""
数据维护服务。

用于在规则升级后批量刷新已有数据的派生字段，避免旧的伪字段或空字段
继续影响事件构建和前端展示。
"""
from database import Info
from services.tech_content_parser import parse_tech_content


def refresh_info_semantics(session, limit: int | None = None) -> dict:
    """重算 Info 的科技语义字段。"""
    query = session.query(Info).filter(Info.is_deleted == 0).order_by(Info.id.asc())
    if limit:
        query = query.limit(limit)

    processed_count = 0
    changed_count = 0
    for info in query.all():
        semantic_result = parse_tech_content(info.title, info.content)
        next_topic = semantic_result.topic_type
        next_entities = ",".join(semantic_result.entities)
        next_keywords = ",".join(semantic_result.keywords)

        if (
            info.tech_topic_type != next_topic
            or info.tech_entities != next_entities
            or info.tech_keywords != next_keywords
        ):
            info.tech_topic_type = next_topic
            info.tech_entities = next_entities
            info.tech_keywords = next_keywords
            changed_count += 1
        processed_count += 1

    session.commit()
    return {
        "processed_count": processed_count,
        "changed_count": changed_count,
    }
