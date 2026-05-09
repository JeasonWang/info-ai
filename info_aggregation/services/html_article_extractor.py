import sys
from services.collection import html_article_extractor as _impl

sys.modules[__name__] = _impl
