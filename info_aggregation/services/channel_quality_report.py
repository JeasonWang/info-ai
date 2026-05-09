import sys
from services.quality import channel_quality_report as _impl

sys.modules[__name__] = _impl
