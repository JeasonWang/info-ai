import sys
from services.quality import data_quality_report as _impl

sys.modules[__name__] = _impl
