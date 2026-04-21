from services.tech_content_parser import parse_tech_content


def test_parse_tech_content_extracts_topic_entity_and_keywords():
    result = parse_tech_content(
        title="英伟达发布H200芯片",
        content="H200 芯片面向大模型训练场景，开发者开始讨论显存、训练效率和部署成本。",
    )

    assert result.topic_type == "chip_release"
    assert "英伟达" in result.entities
    assert "H200" in result.entities
    assert "显存" in result.keywords
    assert "训练效率" in result.keywords


def test_parse_tech_content_marks_dev_tool_topics():
    result = parse_tech_content(
        title="MCP 工具链实践",
        content="文章介绍了开发者如何把 MCP、API 和 Agent 工作流接入现有编程工具。",
    )

    assert result.topic_type == "dev_tool"
    assert "MCP" in result.entities
    assert "API" in result.keywords


def test_parse_tech_content_leaves_non_tech_content_empty():
    result = parse_tech_content(
        title="春日赏花攻略合集",
        content="全国多地进入赏花季，樱花、油菜花、桃花竞相绽放。",
    )

    assert result.topic_type == ""
    assert result.entities == []
    assert result.keywords == []
