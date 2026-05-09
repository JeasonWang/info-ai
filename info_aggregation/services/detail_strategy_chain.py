import sys
from services.collection import detail_strategy_chain as _impl

sys.modules[__name__] = _impl
