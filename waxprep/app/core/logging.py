from loguru import logger
import sys
from waxprep.app.core.config import settings


def setup_logging():
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=settings.debug,
    )

    if settings.app_env == "production":
        logger.add(
            "logs/waxprep_{time:YYYY-MM-DD}.log",
            format=log_format,
            level="INFO",
            rotation="00:00",
            retention="30 days",
            compression="gz",
            backtrace=True,
            diagnose=False,
        )

    return logger
