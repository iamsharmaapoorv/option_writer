import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"
LOG_DIR = Path(__file__).resolve().parent / "logs"


def setup_logging(log_name: str) -> logging.Logger:
    logger = logging.getLogger()
    log_file = LOG_DIR / f"{log_name}.log"

    if getattr(logger, "_option_writer_configured_for", None) == str(log_file):
        return logger

    LOG_DIR.mkdir(exist_ok=True)
    logger.setLevel(logging.INFO)

    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=2,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger._option_writer_configured_for = str(log_file)

    return logger
