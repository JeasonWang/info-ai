import sys
from services.collection import credential_provider as _impl

sys.modules[__name__] = _impl
