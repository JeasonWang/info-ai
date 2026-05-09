import sys
from services.analysis import event_analysis_quality_actions as _impl

sys.modules[__name__] = _impl
