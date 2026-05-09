import sys
from services.collection import detail_replay as _impl

sys.modules[__name__] = _impl
