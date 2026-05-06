from crawlers.xiaohongshu import XiaohongshuCrawler
from services.detail_pipeline import DetailStrategyResult


def test_xiaohongshu_resolve_detail_uses_initial_state_note_content():
    crawler = XiaohongshuCrawler()

    class DummyResponse:
        text = """
        <html><body>
          <script>
          window.__INITIAL_STATE__={
            "note":{
              "noteDetailMap":{
                "abc":{
                  "note":{
                    "title":"AI 工具真实体验",
                    "desc":"这篇笔记分享了 AI 工具在知识整理、旅行规划和工作流自动化中的真实体验。作者详细比较了提示词准备、任务拆解、结果校验和多轮修改过程，并提醒用户关注隐私设置、账号安全和生成内容的准确性。评论区也讨论了不同工具在中文场景下的稳定性和成本差异。"
                  }
                }
              }
            }
          }
          </script>
        </body></html>
        """

    crawler.fetch = lambda *args, **kwargs: DummyResponse()

    result = crawler.resolve_detail(
        {
            "title": "AI 工具真实体验",
            "content": "AI 工具真实体验",
            "source_url": "https://www.xiaohongshu.com/explore/abc",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "xhs_initial_state"
    assert "隐私设置" in result.content


def test_xiaohongshu_feed_desc_is_preserved_for_list_quality():
    crawler = XiaohongshuCrawler()

    item = crawler._extract_note_from_feed(
        {
            "id": "abc",
            "xsecToken": "token",
            "noteCard": {
                "displayTitle": "AI 工具真实体验",
                "desc": "这篇笔记详细分享了提示词准备、任务拆解、结果校验和隐私设置注意事项。",
            },
        }
    )

    assert item["content"].startswith("AI 工具真实体验。")
    assert "隐私设置" in item["content"]
    assert item["_search_content"]


def test_xiaohongshu_feed_card_includes_tags_and_interactions():
    crawler = XiaohongshuCrawler()

    item = crawler._extract_note_from_feed(
        {
            "id": "abc",
            "xsecToken": "token",
            "noteCard": {
                "displayTitle": "AI 工具真实体验",
                "desc": "这篇笔记详细分享了提示词准备、任务拆解和结果校验。",
                "tagList": [{"name": "AI工具"}, {"name": "效率"}],
                "interactInfo": {"likedCount": "1088", "commentCount": "45"},
            },
        }
    )

    assert "AI工具" in item["content"]
    assert "点赞1088" in item["content"]
    assert "评论45" in item["content"]


def test_xiaohongshu_feed_filters_low_information_note():
    crawler = XiaohongshuCrawler()

    item = crawler._extract_note_from_feed(
        {
            "id": "abc",
            "noteCard": {
                "displayTitle": "太绝了",
                "desc": "",
            },
        }
    )

    assert item is None


def test_xiaohongshu_cookie_is_loaded_from_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("XHS_COOKIE=a=1; web_session=abc\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("XHS_COOKIE", raising=False)

    crawler = XiaohongshuCrawler()

    assert crawler._get_xhs_cookie() == "a=1; web_session=abc"
    assert crawler._build_headers()["Cookie"] == "a=1; web_session=abc"


def test_xiaohongshu_resolve_detail_uses_rendered_fallback_when_html_is_empty():
    crawler = XiaohongshuCrawler()

    class EmptyResponse:
        text = "<html><body>你访问的页面不见了</body></html>"

    crawler.fetch = lambda *args, **kwargs: EmptyResponse()
    crawler._fetch_rendered_detail = lambda item: DetailStrategyResult(
        strategy="rendered_page",
        content="AI 工具真实体验。作者分享了提示词准备、任务拆解、结果校验、隐私设置和账号安全注意事项。评论区补充了中文场景稳定性、使用成本和多轮修改经验，适合做工具选型参考。笔记还对比了免费版和付费版在长文整理、表格生成、旅行计划拆解中的表现，并建议先用低风险资料做测试。",
    )

    result = crawler.resolve_detail(
        {
            "title": "AI 工具真实体验",
            "content": "AI 工具真实体验",
            "source_url": "https://www.xiaohongshu.com/explore/abc",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "rendered_page"
    assert "工具选型参考" in result.content


def test_xiaohongshu_note_content_includes_tags_and_interactions():
    crawler = XiaohongshuCrawler()

    content = crawler._combine_note_content(
        {
            "title": "AI 工具真实体验",
            "desc": "这篇笔记分享了知识整理和工作流自动化经验。",
            "tagList": [{"name": "AI工具"}, {"name": "效率工具"}],
            "interactInfo": {"likedCount": "1088", "collectedCount": "321", "commentCount": "45"},
        }
    )

    assert "AI工具" in content
    assert "点赞1088" in content
    assert "收藏321" in content


def test_xiaohongshu_rendered_login_shell_is_rejected():
    crawler = XiaohongshuCrawler()

    crawler.fetch = lambda *args, **kwargs: type("Resp", (), {"text": "<html></html>"})()
    crawler._fetch_rendered_detail = lambda item: DetailStrategyResult(
        strategy="rendered_page",
        content="登录后推荐更懂你的笔记 可用 小红书 或 微信 扫码 手机号登录 获取验证码 我已阅读并同意《用户协议》《隐私政策》",
    )

    result = crawler.resolve_detail(
        {
            "title": "只有想不到，没有做不到",
            "content": "只有想不到，没有做不到",
            "source_url": "https://www.xiaohongshu.com/explore/abc",
        }
    )

    assert result.status == "failed"
    assert result.failure_reason == "shell_page"
