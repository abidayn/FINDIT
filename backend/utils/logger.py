import logging

from config import LOG_LEVEL


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger.

    Every module calls this with its own __name__ so log lines say where they
    came from. We guard against adding a second handler because Python caches
    logger objects by name — calling this twice for the same module would
    otherwise print every line twice.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(LOG_LEVEL)

    return logger
