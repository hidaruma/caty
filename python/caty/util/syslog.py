import logging
import logging.handlers
import os

def get_access_log():
    return logging.getLogger('Caty.AccessLog')

def get_error_log():
    return logging.getLogger('Caty.ErrorLog')

def get_start_log():
    return logging.getLogger('Caty.StartLog')

def get_deprecate_log():
    return logging.getLogger('Caty.DeprecateLog')

def init_log(enc='utf-8', log_dir='.'):
    alogger = logging.getLogger('Caty.AccessLog')
    alogger.setLevel(logging.DEBUG)
    log_file = os.path.join(log_dir, 'access.log')
    handler = logging.handlers.TimedRotatingFileHandler(
              log_file, interval=1, when='D', backupCount=5, encoding=enc)
    alogger.addHandler(handler)

    elogger = logging.getLogger('Caty.ErrorLog')
    elogger.setLevel(logging.ERROR)
    elog_file = os.path.join(log_dir, 'error.log')
    handler = logging.handlers.TimedRotatingFileHandler(
              elog_file, interval=1, when='D', backupCount=5, encoding=enc)
    elogger.addHandler(handler)

    slogger = logging.getLogger('Caty.StartLog')
    slogger.setLevel(logging.DEBUG)
    slog_file = os.path.join(log_dir, 'start.log')
    handler = logging.handlers.TimedRotatingFileHandler(
              slog_file, interval=1, when='D', backupCount=5, encoding=enc)
    slogger.addHandler(handler)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    dlogger = logging.getLogger('Caty.DeprecateLog')
    dlogger.setLevel(logging.DEBUG)
    log_file = os.path.join(log_dir, 'deprecated.log')
    handler = logging.handlers.TimedRotatingFileHandler(
              log_file, interval=1, when='D', backupCount=5, encoding=enc)
    dlogger.addHandler(handler)

