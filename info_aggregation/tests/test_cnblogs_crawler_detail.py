from crawlers.cnblogs import CnblogsCrawler


def test_cnblogs_resolve_detail_prefers_post_body_strategy():
    crawler = CnblogsCrawler()
    article_text = (
        "OpenAI 发布新模型后，开发者开始评估 API 接入方式、上下文管理、工具调用稳定性和企业部署成本。"
        "文章第一部分分析模型能力变化，包括推理速度、长上下文窗口、函数调用准确率和多步骤任务拆解能力。"
        "文章第二部分给出工程实践建议，团队需要在灰度环境中验证提示词兼容性、接口响应格式和异常重试策略。"
        "文章第三部分讨论监控治理，包括请求耗时、失败率、成本预算、权限边界和数据安全审计。"
        "最后作者给出迁移方案，建议先从内部知识库、客服助手和代码生成场景开始试点，再逐步扩大到生产流程。"
        "这些内容构成完整的技术文章正文，而不是列表摘要或导航文本。"
        "作者还补充了落地检查清单：第一步整理现有调用链路，第二步梳理提示词和工具 schema，第三步准备回归测试集合，"
        "第四步在灰度环境对比旧模型和新模型的准确率、耗时、成本和错误类型，第五步根据监控结果决定是否扩大流量。"
        "这类内容可以支撑后续技术事件分析，帮助判断新模型对开发流程、企业架构和团队协作方式的实际影响。"
        "文章末尾还提醒读者关注缓存策略、限流策略、数据脱敏、审计日志和灾备回滚方案，避免只看模型效果而忽略工程可靠性。"
        "如果团队已经有多模型路由，还需要评估新模型和旧模型在不同任务类型上的性价比，并把评估结果写入持续集成流程。"
    )

    class DummyResponse:
        text = f"""
        <html>
          <body>
            <nav>首页 登录 注册 推荐</nav>
            <div id="cnblogs_post_body">
              <p>{article_text}</p>
            </div>
            <div id="blog-comments-placeholder">评论区内容不应进入正文</div>
          </body>
        </html>
        """

    crawler.fetch = lambda *args, **kwargs: DummyResponse()

    result = crawler.resolve_detail(
        {
            "title": "OpenAI 发布新模型",
            "content": "列表摘要",
            "source_url": "https://www.cnblogs.com/demo/p/123456.html",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "cnblogs_post_body"
    assert result.content_length >= 500
    assert "灰度环境" in result.content
    assert "评论区内容" not in result.content
