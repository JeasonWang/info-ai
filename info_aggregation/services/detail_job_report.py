import sys
from services.quality import detail_job_report as _impl

sys.modules[__name__] = _impl
