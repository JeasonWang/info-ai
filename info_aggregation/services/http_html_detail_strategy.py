import sys
from services.collection import http_html_detail_strategy as _impl

sys.modules[__name__] = _impl
