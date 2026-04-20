from services.detail_pipeline import DetailStrategyResult, run_detail_pipeline


def test_pipeline_marks_shell_page_as_failed():
    result = run_detail_pipeline(
        title="微博热点",
        list_content="微博热点",
        strategy_results=[
            DetailStrategyResult(
                strategy="web_fallback",
                content="你访问的页面不见了 沪ICP备 营业执照",
            )
        ],
    )

    assert result.status == "failed"
    assert result.failure_reason == "shell_page"
    assert result.score == 0


def test_pipeline_marks_multi_source_content_as_complete():
    result = run_detail_pipeline(
        title="OpenAI 新发布会",
        list_content="列表摘要",
        strategy_results=[
            DetailStrategyResult(
                strategy="topic_search",
                content="OpenAI 发布会上介绍了新模型、价格、开放计划。多位用户转发现场重点，并讨论开发者接入方式。",
            )
        ],
    )

    assert result.status == "complete"
    assert result.strategy == "topic_search"
    assert result.score >= 80
    assert result.content_length >= 40


def test_pipeline_recognizes_relevant_mixed_keyword_content_as_complete():
    result = run_detail_pipeline(
        title="英伟达发布H200芯片",
        list_content="列表摘要",
        strategy_results=[
            DetailStrategyResult(
                strategy="topic_search",
                content="H200芯片性能进一步提升，开发者开始讨论显存、训练效率和部署成本变化，产业侧也在评估新一代训练集群的升级节奏。",
            )
        ],
    )

    assert result.status == "complete"
    assert result.strategy == "topic_search"
    assert result.failure_reason == ""
