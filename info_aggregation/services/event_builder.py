import sys
from services.analysis import event_builder as _impl

sys.modules[__name__] = _impl
