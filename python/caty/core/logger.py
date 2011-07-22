# coding:utf-8
import logging
import logging.handlers
from caty.core.async import DLock
from caty.core.facility import FakeFacility
from caty.util.path import join

def init(app, type):
    log = logging.getLogger('Caty.%s.%s' % (str(app.name), type))
    log.setLevel(logging.DEBUG)
    log_file = join(str(app._group.name), str(app.name), '%s.log' % type)
    handler = TimedRotatingFileHandlerWithLock(
          log_file, interval=1, when='D', backupCount=5, encoding=app._system.sysencoding)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    log.addHandler(handler)

def get(name, type):
    return logging.getLogger('Caty.%s.%s' % (name, type))

class TimedRotatingFileHandlerWithLock(logging.handlers.TimedRotatingFileHandler):
    def emit(self, record):
        with DLock(self.baseFilename):
            logging.handlers.TimedRotatingFileHandler.emit(self, record)

class Logger(FakeFacility):
    def __init__(self, app):
        self._app = app

    @property
    def exec_log(self):
        return self._app.get_logger('exec')
    
    @property
    def app_log(self):
        return self._app.get_logger('app')
    

