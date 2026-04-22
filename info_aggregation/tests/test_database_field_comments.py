from database import Base


def test_database_columns_have_chinese_comments():
    missing_comments: list[str] = []

    for table in Base.metadata.sorted_tables:
        for column in table.columns:
            if not column.comment or not column.comment.strip():
                missing_comments.append(f"{table.name}.{column.name}")

    assert missing_comments == []
