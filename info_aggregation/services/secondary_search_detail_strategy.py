import sys
from services.collection import secondary_search_detail_strategy as _impl

sys.modules[__name__] = _impl
