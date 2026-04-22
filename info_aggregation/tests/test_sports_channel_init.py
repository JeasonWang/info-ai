from config import CATEGORY_SPORTS
from database import Category, Channel
from sql.init_data import init_categories, init_channels


def test_init_data_creates_sports_category_and_channels(session):
    category_map = init_categories(session)
    channel_map = init_channels(session, category_map)

    sports = session.query(Category).filter(Category.code == "sports").first()
    cctv = session.query(Channel).filter(Channel.code == "cctv_sports").first()
    sina = session.query(Channel).filter(Channel.code == "sina_sports").first()

    assert category_map[CATEGORY_SPORTS] == sports.id
    assert channel_map["cctv_sports"] == cctv.id
    assert channel_map["sina_sports"] == sina.id
    assert cctv.category_id == sports.id
    assert sina.category_id == sports.id
    assert cctv.is_active == 1
    assert sina.is_active == 1
