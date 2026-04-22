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


def test_parse_tech_content_recognizes_ai_product_and_sql_tool_samples():
    moonshot = parse_tech_content(
        title="月之暗面发布K2.6，杨植麟真的需要一个郭达雅",
        content="Kimi K2.6 面向 AI 应用场景升级，行业继续关注模型能力和产品化节奏。",
    )
    typed_sql = parse_tech_content(
        title="TypedSql：在 C# 类型系统上实现一个 SQL 查询引擎",
        content="开发者用 C# 类型系统实现 SQL 查询引擎，重点讨论类型安全和数据库查询体验。",
    )

    assert moonshot.topic_type == "model_release"
    assert "月之暗面" in moonshot.entities
    assert "Kimi" in moonshot.entities
    assert "AI应用" in moonshot.keywords
    assert typed_sql.topic_type == "dev_tool"
    assert "C#" in typed_sql.entities
    assert "SQL" in typed_sql.keywords


def test_parse_tech_content_recognizes_infra_and_runtime_samples():
    oom = parse_tech_content(
        title="生产事故-那些年遇到过的OOM",
        content="文章复盘 Java 服务 OOM、内存泄漏和线上故障排查过程。",
    )
    keepalived = parse_tech_content(
        title="Keepalived详解：原理、编译安装与高可用集群配置",
        content="介绍 Keepalived 在高可用集群中的配置方式和故障切换机制。",
    )

    assert oom.topic_type == "dev_tool"
    assert "OOM" in oom.entities
    assert "故障排查" in oom.keywords
    assert keepalived.topic_type == "dev_tool"
    assert "Keepalived" in keepalived.entities
    assert "高可用" in keepalived.keywords


def test_parse_tech_content_recognizes_ai_developer_news_samples():
    gpt = parse_tech_content(
        title="突然变强，速度翻4倍，GPT Pro惊现“神级”操作，网友怀疑GPT-5.5已就",
        content="GPT Pro 在推理速度和模型能力上出现明显提升，开发者继续关注 GPT-5.5。",
    )
    claude_md = parse_tech_content(
        title="一个CLAUDE.md霸榜GitHub第一，蒸馏自Karpathy，6万码农抄作",
        content="CLAUDE.md 在 GitHub 开源项目中流行，开发者讨论提示词、代码生成和蒸馏经验。",
    )

    assert gpt.topic_type == "model_release"
    assert "GPT" in gpt.entities
    assert "GPT-5.5" in gpt.entities
    assert "推理速度" in gpt.keywords
    assert claude_md.topic_type == "dev_tool"
    assert "GitHub" in claude_md.entities
    assert "Karpathy" in claude_md.entities
    assert "代码生成" in claude_md.keywords
