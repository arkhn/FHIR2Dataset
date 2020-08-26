from functools import wraps
from time import time
import logging

logger = logging.getLogger(__name__)


def timing(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        logger.debug(f"func:{f.__qualname__}\ntook: {te-ts:2.6f} sec")
        return result

    return wrap
