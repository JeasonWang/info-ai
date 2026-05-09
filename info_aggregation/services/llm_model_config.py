import sys
from services.analysis import llm_model_config as _impl

sys.modules[__name__] = _impl
