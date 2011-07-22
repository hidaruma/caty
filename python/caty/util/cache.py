#coding: utf-8
from __future__ import with_statement
import itertools
from threading import RLock
from time import time

__all__ = ['Cache', 'memoize']

class Cache(object):
    def __init__(self, size):
        self._cache_entries = {}
        self._cache_frequency = {}
        self._cache_num = 0
        self._cache_size = size
        self._sweep_size = int(size / 10)

    def get(self, key, default=None):
        r = self._cache_entries.get(key, default)
        if r is None:
            return r
        else:
            return r.value

    def set(self, key, value):
        with RLock():
            if key in self._cache_entries: return
            self._cache_entries[key] = CacheEntry(key, value, self)
            self._cache_frequency[key] = (0, -time())
            self._cache_num += 1
            if self._cache_num >= self._cache_size:
                self.sweep()
    
    def emit(self, key):
        with RLock():
            v = self._cache_frequency[key]
            self._cache_frequency[key] = (v[0]+1, v[1])

    def sweep(self):
        # 使用回数と挿入時刻でソートし、先頭 1..n+1 の要素を削除
        # 0..n でないのは、挿入されたばかりの要素が削除されることを防ぐため
        l = itertools.islice(sorted(
                                ((k, v) for k, v in self._cache_frequency.items()),
                                key=lambda a:a[1]
                             ), 1, self._sweep_size+1)
        for k, v in l:
            del self._cache_entries[k]
            del self._cache_frequency[k]
            self._cache_num -= 1

class CacheEntry(object):
    def __init__(self, key, value, cache):
        self._value = value
        self._key = key
        self._cache = cache

    @property
    def value(self):
        self._cache.emit(self._key)
        return self._value

class memoize(object):
    u"""関数にキャッシュ機能をつける。
    """
    def __init__(self, f):
        self.__function = f
        self.__cache = {}


    def __call__(self, *args):
        f = self.__function
        cache = self.__cache
        with RLock():
            if args in cache:
                return cache[args]
            else:
                cache[args] = f(*args)
                return cache[args]

    def clear(self):
        u"""キャッシュのクリアを行う。
        """
        self.__cache = {}


