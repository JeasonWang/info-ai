from crawlers.cctv_sports import CctvSportsCrawler
from crawlers.sina_sports import SinaSportsCrawler


class DummyResponse:
    def __init__(self, text: str):
        self.text = text


def test_cctv_sports_crawler_extracts_homepage_links_and_detail_content():
    crawler = CctvSportsCrawler()

    homepage_html = """
    <li>
      <a href="https://sports.cctv.com/2026/04/21/ARTIabc.shtml">手感不错 吴宜泽领先雷佩凡</a>
    </li>
    <li>
      <a href="//sports.cctv.com/2026/04/21/ARTIxyz.shtml">文班亚马当选年度最佳防守球员</a>
    </li>
    <li>
      <a href="https://tv.cctv.com/2026/04/21/VIDEabc.shtml">这个视频页应该跳过</a>
    </li>
    """
    detail_html = """
    <html><body>
      <div class="content_area">
        <p>斯诺克世锦赛首轮继续进行，吴宜泽在比赛中展现出稳定手感。</p>
        <p>他通过连续得分建立优势，后续赛程仍将受到球迷关注。</p>
      </div>
    </body></html>
    """

    def fake_fetch(url, *args, **kwargs):
        if url == crawler.HOME_URL:
            return DummyResponse(homepage_html)
        return DummyResponse(detail_html)

    crawler.fetch = fake_fetch

    items = crawler.crawl()
    detail = crawler.fetch_detail(items[0]["source_url"], items[0])

    assert len(items) == 2
    assert items[0]["title"] == "手感不错 吴宜泽领先雷佩凡"
    assert items[0]["source_url"] == "https://sports.cctv.com/2026/04/21/ARTIabc.shtml"
    assert "吴宜泽在比赛中展现出稳定手感" in detail


def test_sina_sports_crawler_filters_lottery_links_and_reads_article_body():
    crawler = SinaSportsCrawler()

    homepage_html = """
    <a href="https://sports.sina.com.cn/golf/pgatour/2026-03-16/doc-demo001.shtml">
      球员锦标赛卡梅隆杨逆袭夺冠
    </a>
    <a href="https://sports.sina.com.cn/l/2026-03-16/doc-lottery.shtml">
      大乐透头奖开出千万大奖
    </a>
    """
    detail_html = """
    <html><body>
      <div id="artibody">
        <p>球员锦标赛收官轮竞争激烈，卡梅隆杨在最后阶段完成逆袭。</p>
        <p>这场胜利让他在积分榜上的位置进一步提升。</p>
      </div>
    </body></html>
    """

    def fake_fetch(url, *args, **kwargs):
        if url == crawler.HOME_URL:
            return DummyResponse(homepage_html)
        return DummyResponse(detail_html)

    crawler.fetch = fake_fetch

    items = crawler.crawl()
    detail = crawler.fetch_detail(items[0]["source_url"], items[0])

    assert len(items) == 1
    assert items[0]["title"] == "球员锦标赛卡梅隆杨逆袭夺冠"
    assert "大乐透" not in items[0]["title"]
    assert "卡梅隆杨在最后阶段完成逆袭" in detail
