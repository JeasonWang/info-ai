import sys
from services.collection import detail_jobs as _impl

sys.modules[__name__] = _impl
