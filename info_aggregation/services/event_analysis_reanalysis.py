import sys
from services.analysis import event_analysis_reanalysis as _impl

sys.modules[__name__] = _impl
