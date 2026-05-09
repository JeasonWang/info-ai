import sys
from services.collection import detail_job_worker as _impl

sys.modules[__name__] = _impl
