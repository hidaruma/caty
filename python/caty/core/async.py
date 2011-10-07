from __future__ import with_statement
from caty.core.facility import TransactionAdaptor
from threading import Thread, RLock
try:
    import multiprocessing
except:
    multiprocessing = None
import time
import types

class AsyncQueue(object):
    def __init__(self, app):
        self._app = app
        self._queue = {}
    
    def push(self, callee, func, *args, **kwds):
        if self._app._system.useMultiprocessing:
            t = AsyncProcess(self, callee, func, *args, **kwds)
        else:
            t = AsyncThread(self, callee, func, *args, **kwds)
        t.start()

    def remove(self, name):
        with RLock():
            del self._queue[name]
    
class AsyncWorker(object):
    def __init__(self, creator, callee, func, *args, **kwds):
        self._creator = creator
        self._func = func
        self._args = args
        self._kwds = kwds
        self._obj = callee
        self._callee = callee

    def run(self):
        try:
            with RLock():
                self._creator._queue[self.getName()] = self.get_worker_id()
            if isinstance(self._callee, TransactionAdaptor):
                self._callee.reset_facility()
            time.sleep(1)
            if isinstance(self._func, types.MethodType) and type(self._func.im_self) == type(self._obj):
                self._func.im_func(self._obj, *self._args, **self._kwds)
            else:
                self._func(self._obj, *self._args, **self._kwds)
        finally:
            self._finalize()

class AsyncThread(AsyncWorker, Thread):
    def __init__(self, *args, **kwds):
        Thread.__init__(self)
        AsyncWorker.__init__(self, *args, **kwds)
        
    def get_worker_id(self):
        return self.ident

    def _finalize(self):
        self._creator.remove(self.getName())

if multiprocessing:
    class AsyncProcess(AsyncWorker, multiprocessing.Process):
        def __init__(self, *args, **kwds):
            multiprocessing.Process.__init__(self)
            AsyncWorker.__init__(self, *args, **kwds)

        def getName(self):
            return self.name

        def get_worker_id(self):
            return self.pid

        def _finalize(self):
            pass

else:
    AsyncProcess = AsyncThread

import os
import tempfile
import time
class DLock(object):
    def __init__(self, lock_id):
        self._lock_id = lock_id
        self._path = tempfile.gettempdir() + os.path.sep + lock_id.replace(os.path.sep, '__').replace('!', '!!').replace(':', '!') + '.lockdir'

    def __enter__(self):
        while os.path.exists(self._path):
            time.sleep(0.1)
        try:
            os.mkdir(self._path)
        except:
            self.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        if os.path.exists(self._path):
            os.rmdir(self._path)
        if not exc_type and not exc_value and not traceback:
            return True
        else:
            return False
