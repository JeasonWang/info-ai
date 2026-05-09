import sys
from services.enrichment import tech_content_parser as _impl

sys.modules[__name__] = _impl
