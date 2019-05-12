import logging


LOGGING_FORMAT = "%(levelname)s:%(name)s:%(funcName)s: %(message)s"
LOGGING_LEVEL = logging.ERROR
DEBUG_REQ_FMT = """
  TYPE: Request
  FUNC: %s
   URL: %s
METHOD: %s
PARAMS: %s
  DATA: %s
"""

DEBUG_RES_FMT = """
   TYPE: Response
   FUNC: %s
 STATUS: %s
CONTENT: %s
"""

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(LOGGING_FORMAT)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(LOGGING_LEVEL)