import sys
from services.analysis import event_analysis_quality_report as _impl

sys.modules[__name__] = _impl
