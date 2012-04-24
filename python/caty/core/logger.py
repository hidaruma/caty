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

    def doRollover(self):
        if self.stream:
            self.stream.close()
        t = self.rolloverAt - self.interval
        if self.utc:
            timeTuple = time.gmtime(t)
        else:
            timeTuple = time.localtime(t)
        dfn = self.baseFilename.replace('.log', '') + "." + time.strftime(self.suffix, timeTuple) + '.log'
        if os.path.exists(dfn):
            os.remove(dfn)
        os.rename(self.baseFilename, dfn)
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)
        self.mode = 'w'
        self.stream = self._open()
        currentTime = int(time.time())
        newRolloverAt = self.computeRollover(currentTime)
        while newRolloverAt <= currentTime:
            newRolloverAt = newRolloverAt + self.interval
        if (self.when == 'MIDNIGHT' or self.when.startswith('W')) and not self.utc:
            dstNow = time.localtime(currentTime)[-1]
            dstAtRollover = time.localtime(newRolloverAt)[-1]
            if dstNow != dstAtRollover:
                if not dstNow:  # DST kicks in before next rollover, so we need to deduct an hour
                    newRolloverAt = newRolloverAt - 3600
                else:           # DST bows out before next rollover, so we need to add an hour
                    newRolloverAt = newRolloverAt + 3600
        self.rolloverAt = newRolloverAt


class Logger(FakeFacility):
    def __init__(self, app):
        self._app = app

    @property
    def exec_log(self):
        return self._app.get_logger('exec')
    
    @property
    def app_log(self):
        return self._app.get_logger('app')
    

