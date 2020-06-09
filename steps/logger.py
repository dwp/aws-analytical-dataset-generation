import logging
import os


def setup_logging(log_path):
    log_level = os.environ["ADG_LOG_LEVEL"].upper() if "ADG_LOG_LEVEL" in os.environ else "INFO"
    the_logger = logging.getLogger()
    for old_handler in the_logger.handlers:
        the_logger.removeHandler(old_handler)

    file_hander = logging.FileHandler(log_path)

    json_format = "{ 'timestamp': '%(asctime)s', 'log_level': '%(levelname)s', 'message': '%(message)s' }"
    file_hander.setFormatter(logging.Formatter(json_format))
    the_logger.addHandler(file_hander)
    new_level = logging.getLevelName(log_level.upper())
    the_logger.setLevel(new_level)

    return the_logger


if __name__ == "__main__":
    logger_path = "hive_tables_creation_log.txt"
    logger = setup_logging(level, logger_path)
    logger.info("Logging information")
