import logging

LOG_INFO_FILE = '/var/log/cicflowmeter/cicflowmeter.log'
LOG_ERROR_FILE = '/var/log/cicflowmeter/error.log'

_log_format = f"%(asctime)s[%(levelname)s][%(thread)d-%(threadName)s] %(filename)s:%(funcName)s(%(lineno)d) %(message)s"


def get_file_handler():
    file_handler = logging.FileHandler(LOG_INFO_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_log_format))
    return file_handler


def get_file_handler_error():
    file_handler = logging.FileHandler(LOG_ERROR_FILE)
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(logging.Formatter(_log_format))
    return file_handler


def get_stream_handler():
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter(_log_format))
    return stream_handler


def get_logger(name: str = None, level: int = logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(get_file_handler())
    logger.addHandler(get_file_handler_error())
    logger.addHandler(get_stream_handler())
    return logger


log = get_logger()
