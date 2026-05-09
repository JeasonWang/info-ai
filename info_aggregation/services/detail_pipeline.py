import sys
from services.collection import detail_pipeline as _impl

sys.modules[__name__] = _impl
