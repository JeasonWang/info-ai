import json

from crawlers.reuters import ReutersCrawler


def test_reuters_resolve_detail_prefers_article_api_paragraphs():
    crawler = ReutersCrawler()

    class DummyResponse:
        def json(self):
            return {
                "result": {
                    "content_items": [
                        {"type": "paragraph", "content": "OpenAI released a new model on Tuesday, according to company officials."},
                        {"type": "paragraph", "content": "Developers said the update could change API costs, enterprise deployment plans and automation workflows."},
                        {"type": "paragraph", "content": "Analysts said companies will watch reliability, governance and data controls before moving production traffic."},
                        {"type": "paragraph", "content": "The announcement adds pressure on rivals as customers compare model quality, latency and tooling support."},
                        {"type": "paragraph", "content": "Reuters reported that market participants expect more investment in AI infrastructure through the year."},
                        {"type": "paragraph", "content": "Executives said adoption would depend on audit controls, regional compliance requirements and the ability to monitor automated decisions across business units."},
                        {"type": "paragraph", "content": "Industry analysts added that demand for chips, cloud capacity and integration services could rise if large customers move more workloads to the new model."},
                    ]
                }
            }

    crawler.session.post = lambda *args, **kwargs: DummyResponse()
    crawler.fetch = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not use web fallback"))

    result = crawler.resolve_detail(
        {
            "title": "OpenAI released a new model",
            "content": "Short summary",
            "source_url": "https://www.reuters.com/technology/openai-model-2026-05-02/",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "reuters_article_api"
    assert "enterprise deployment plans" in result.content


def test_reuters_resolve_detail_uses_json_ld_when_api_is_empty():
    crawler = ReutersCrawler()

    class EmptyApiResponse:
        def json(self):
            return {"result": {}}

    class HtmlResponse:
        text = """
        <html><head>
          <script type="application/ld+json">
          {
            "@type": "NewsArticle",
            "articleBody": "OpenAI released a new model on Tuesday, according to company officials. Developers said the update could change API costs, enterprise deployment plans and automation workflows. Analysts said companies will watch reliability, governance and data controls before moving production traffic. The announcement adds pressure on rivals as customers compare model quality, latency and tooling support. Reuters reported that market participants expect more investment in AI infrastructure through the year. Executives said adoption would depend on audit controls, regional compliance requirements and the ability to monitor automated decisions across business units. Industry analysts added that demand for chips, cloud capacity and integration services could rise if large customers move more workloads to the new model."
          }
          </script>
        </head><body>Subscribe banner</body></html>
        """

    crawler.session.post = lambda *args, **kwargs: EmptyApiResponse()
    crawler.fetch = lambda *args, **kwargs: HtmlResponse()

    result = crawler.resolve_detail(
        {
            "title": "OpenAI released a new model",
            "content": "Short summary",
            "source_url": "https://www.reuters.com/technology/openai-model-2026-05-02/",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "reuters_json_ld"
    assert "governance and data controls" in result.content


def test_reuters_google_news_index_restores_reuters_leads():
    crawler = ReutersCrawler()

    class DummyResponse:
        text = """
        <rss><channel>
          <item>
            <title>Global markets rise as officials meet - Reuters</title>
            <link>https://news.google.com/rss/articles/example</link>
            <source>Reuters</source>
            <description><![CDATA[<a href="https://www.reuters.com/world/example/">Global markets rise as officials meet</a>&nbsp; Reuters reported market participants were watching policy signals.]]></description>
          </item>
          <item>
            <title>Other source headline</title>
            <link>https://example.com/story</link>
            <source>Example</source>
            <description>Not Reuters</description>
          </item>
        </channel></rss>
        """

    crawler.fetch = lambda *args, **kwargs: DummyResponse()

    items = crawler._crawl_google_news_index()

    assert len(items) == 1
    assert items[0]["title"] == "Global markets rise as officials meet"
    assert items[0]["_reuters_source"] == "google_news_index"
    assert items[0]["source_url"] == "https://www.reuters.com/world/example/"
    assert items[0]["_reuters_lineage"] == "official_url_from_index"
    assert "Reuters reported" in items[0]["content"]


def test_reuters_google_news_index_summary_is_treated_as_partial_detail():
    crawler = ReutersCrawler()

    result = crawler.resolve_detail(
        {
            "title": "Global markets rise as officials meet",
            "content": "Global markets rise as officials meet Reuters reported market participants were watching policy signals and government comments.",
            "source_url": "https://news.google.com/rss/articles/example",
            "_reuters_source": "google_news_index",
        }
    )

    assert result.status in {"partial", "complete"}
    assert result.strategy == "news_index_summary"


def test_reuters_google_news_with_official_url_tries_full_detail_before_summary():
    crawler = ReutersCrawler()

    class ApiResponse:
        def json(self):
            return {
                "result": {
                    "content_items": [
                        {"type": "paragraph", "content": "Global markets rose on Tuesday, according to officials familiar with the talks."},
                        {"type": "paragraph", "content": "Investors said the meeting could affect government bond yields, currency markets and company financing plans."},
                        {"type": "paragraph", "content": "Analysts said companies will watch policy signals, trade conditions and energy prices before changing investment plans."},
                        {"type": "paragraph", "content": "The discussions added pressure on officials as markets compared growth forecasts, inflation data and central bank comments."},
                        {"type": "paragraph", "content": "Reuters reported that market participants expect more volatility if governments do not clarify the next policy steps."},
                        {"type": "paragraph", "content": "Executives said the outcome would shape supply chains, capital spending and risk controls across several industries."},
                        {"type": "paragraph", "content": "Economists added that demand, employment and company margins could shift if policy guidance changes over the coming quarter."},
                    ]
                }
            }

    crawler.session.post = lambda *args, **kwargs: ApiResponse()
    crawler.fetch = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("web fallback should not run"))

    result = crawler.resolve_detail(
        {
            "title": "Global markets rise as officials meet",
            "content": "Reuters reported market participants were watching policy signals.",
            "source_url": "https://www.reuters.com/world/example/",
            "_reuters_source": "google_news_index",
        }
    )

    assert result.status == "complete"
    assert result.strategy == "reuters_article_api"
    assert "company financing plans" in result.content


def test_reuters_news_sitemap_restores_official_urls():
    crawler = ReutersCrawler()

    class DummyResponse:
        text = """
        <?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
          <url>
            <loc>https://www.reuters.com/sports/baseball/example-2026-05-03/</loc>
            <news:news><news:title>Sports story</news:title><news:publication_date>2026-05-03T01:00:00Z</news:publication_date></news:news>
          </url>
          <url>
            <loc>https://www.reuters.com/world/us/trump-says-us-could-restart-iran-strikes-2026-05-02/</loc>
            <news:news><news:title>Trump says US could restart Iran strikes if they misbehave</news:title><news:publication_date>2026-05-02T22:41:43Z</news:publication_date></news:news>
          </url>
        </urlset>
        """

    crawler.fetch = lambda *args, **kwargs: DummyResponse()

    items = crawler._crawl_news_sitemap()

    assert len(items) == 1
    assert items[0]["source_url"].startswith("https://www.reuters.com/world/")
    assert items[0]["_reuters_source"] == "news_sitemap"
    assert "Published at 2026-05-02" in items[0]["content"]


def test_reuters_news_sitemap_metadata_does_not_trigger_blocked_detail_requests():
    crawler = ReutersCrawler()
    calls = {"post": 0, "fetch": 0}

    def fake_post(*args, **kwargs):
        calls["post"] += 1
        raise RuntimeError("should not call article api")

    def fake_fetch(*args, **kwargs):
        calls["fetch"] += 1
        raise RuntimeError("should not call article page")

    crawler.session.post = fake_post
    crawler.fetch = fake_fetch

    result = crawler.resolve_detail(
        {
            "title": "Trump says US could restart Iran strikes",
            "content": (
                "Trump says US could restart Iran strikes. Reuters Published at 2026-05-02T22:41:43Z "
                "according to its official news sitemap. Official Reuters URL: https://www.reuters.com/world/example/"
            ),
            "source_url": "https://www.reuters.com/world/example/",
            "_reuters_source": "news_sitemap",
        }
    )

    assert result.status == "partial"
    assert result.strategy == "news_sitemap_metadata"
    assert calls == {"post": 0, "fetch": 0}
