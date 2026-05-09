import sys
from services.collection import acquisition_quality as _impl

sys.modules[__name__] = _impl
