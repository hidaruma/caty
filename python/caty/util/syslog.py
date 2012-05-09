import logging
import logging.handlers
import os
import time
from caty.core.async import DLock

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
    handler = TimedRotatingFileHandlerWithLock(
              log_file, interval=1, when='D', backupCount=5, encoding=enc)
    alogger.addHandler(handler)

    elogger = logging.getLogger('Caty.ErrorLog')
    elogger.setLevel(logging.ERROR)
    elog_file = os.path.join(log_dir, 'error.log')
    handler = TimedRotatingFileHandlerWithLock(
              elog_file, interval=1, when='D', backupCount=5, encoding=enc)
    elogger.addHandler(handler)

    slogger = logging.getLogger('Caty.StartLog')
    slogger.setLevel(logging.DEBUG)
    slog_file = os.path.join(log_dir, 'start.log')
    handler = TimedRotatingFileHandlerWithLock(
              slog_file, interval=1, when='D', backupCount=5, encoding=enc)
    slogger.addHandler(handler)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    dlogger = logging.getLogger('Caty.DeprecateLog')
    dlogger.setLevel(logging.DEBUG)
    log_file = os.path.join(log_dir, 'deprecated.log')
    handler = TimedRotatingFileHandlerWithLock(
              log_file, interval=1, when='D', backupCount=5, encoding=enc)
    dlogger.addHandler(handler)

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


    def getFilesToDelete(self):
        dirName, baseName = os.path.split(self.baseFilename)
        fileNames = os.listdir(dirName)
        result = []
        prefix = baseName.replace('.log', '') + "."
        plen = len(prefix)
        for fileName in fileNames:
            if fileName[:plen] == prefix:
                suffix = fileName[plen:]
                if self.extMatch.match(suffix):
                    result.append(os.path.join(dirName, fileName))
        result.sort()
        if len(result) < self.backupCount:
            result = []
        else:
            result = result[:len(result) - self.backupCount]
        return result

