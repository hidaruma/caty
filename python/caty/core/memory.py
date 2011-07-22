#coding: utf-8
from caty.core.facility import Facility, AccessManager, READ

class AppMemory(Facility):
    am = AccessManager()

    def __init__(self):
        self._data = {}
        Facility.__init__(self, READ)
        self._initialized = True

    def start(self):
        return self

    def clone(self):
        return self

    @am.update
    def __setitem__(self, k, v):
        self._data[k] = v

    @am.read
    def __getitem__(self, k):
        return self._data[k]

    @am.read
    def get(self, k, default=None):
        return self._data.get(k, default)

    def __contains__(self, key):
        return key in self._data

