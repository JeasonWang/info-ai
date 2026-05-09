import sys
from services.quality import data_maintenance as _impl

sys.modules[__name__] = _impl
