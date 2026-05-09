import sys
from services.quality import data_quality as _impl

sys.modules[__name__] = _impl
