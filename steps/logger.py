import logging
import os
import sys

def setup_logging(log_level, log_path):
    the_logger = logging.getLogger()
    for old_handler in the_logger.handlers:
        the_logger.removeHandler(old_handler)

    if log_path is None:
        handler = logging.StreamHandler(sys.stdout)
    else:
        handler = logging.FileHandler(log_path)

    json_format = "{ 'timestamp': '%(asctime)s', 'log_level': '%(levelname)s', 'message': '%(message)s' }"
    handler.setFormatter(logging.Formatter(json_format))
    the_logger.addHandler(handler)
    new_level = logging.getLevelName(log_level.upper())
    the_logger.setLevel(new_level)

    return the_logger


if __name__ == "__main__":
    logger_path = "hive_tables_creation_log.txt"
    logger = setup_logging(level, logger_path)
    logger.info("Logging information")
