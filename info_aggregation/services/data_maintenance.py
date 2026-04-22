"""
数据维护服务。

用于在规则升级后批量刷新已有数据的派生字段，避免旧的伪字段或空字段
继续影响事件构建和前端展示。
"""
from database import Info
from services.data_quality import is_low_quality_list_item, is_title_content_duplicate, is_unusable_detail_content
from services.tech_content_parser import parse_tech_content


def _normalize_dedupe_key(value: str) -> str:
    """生成标题去重键，忽略空白和大小写差异。"""
    return " ".join((value or "").split()).strip().lower()


def _maintenance_quality_score(info: Info) -> float:
    """计算维护任务中的保留优先级，分数越高越应该保留。"""
    status_bonus = {
        "complete": 60,
        "partial": 35,
        "pending": 10,
        "list_only": 0,
        "failed": -30,
    }.get(info.detail_fetch_status or "", 0)
    return status_bonus + (info.detail_score or 0) + min(info.detail_content_length or len(info.content or ""), 80)


def _should_archive_info(info: Info) -> bool:
    """判断内容是否低质到应该从用户侧数据池软删除。"""
    if is_title_content_duplicate(info.title, info.content):
        return True
    if is_unusable_detail_content(info.content):
        return True
    if (info.detail_fetch_status or "") in {"failed", "list_only"} and is_low_quality_list_item(info.title, info.content):
        return True
    return False


def archive_low_quality_infos(session, limit: int | None = None) -> dict:
    """软删除明显低质量内容，避免它继续进入事件流和页面展示。"""
    query = session.query(Info).filter(Info.is_deleted == 0).order_by(Info.id.asc())
    if limit:
        query = query.limit(limit)

    scanned_count = 0
    archived_count = 0
    for info in query.all():
        scanned_count += 1
        if not _should_archive_info(info):
            continue
        info.is_deleted = 1
        archived_count += 1

    session.commit()
    return {
        "scanned_count": scanned_count,
        "archived_count": archived_count,
    }


def archive_duplicate_title_infos(session) -> dict:
    """软删除重复标题内容，每组只保留质量最高的一条。"""
    infos = session.query(Info).filter(Info.is_deleted == 0).order_by(Info.id.asc()).all()
    groups: dict[str, list[Info]] = {}
    for info in infos:
        key = _normalize_dedupe_key(info.title)
        if not key:
            continue
        groups.setdefault(key, []).append(info)

    duplicate_group_count = 0
    archived_count = 0
    for group in groups.values():
        if len(group) <= 1:
            continue
        duplicate_group_count += 1
        keep = sorted(group, key=_maintenance_quality_score, reverse=True)[0]
        for info in group:
            if info.id == keep.id:
                continue
            info.is_deleted = 1
            archived_count += 1

    session.commit()
    return {
        "duplicate_group_count": duplicate_group_count,
        "archived_count": archived_count,
    }


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
