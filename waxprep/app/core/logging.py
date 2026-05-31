from loguru import logger
import sys
from waxprep.app.core.config import settings

def setup_logging():
    logger.remove()
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    logger.add(sys.stdout, format=log_format, level=settings.log_level, colorize=True, backtrace=True, diagnose=settings.debug)
    return logger
