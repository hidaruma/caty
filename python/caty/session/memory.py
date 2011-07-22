# coding: utf-8
from __future__ import with_statement
from caty.session.value import SessionInfo, SessionInfoWrapper
from caty.session.base import SessionStorage
from caty.jsontools import json
from caty.jsontools.path import build_query
from threading import RLock
from hashlib import sha1
from time import time
import random
import sys

class OnMemoryStorage(SessionStorage):
    u"""セッションデータ一覧を保持し、セッション情報の取得と永続化を行う。
    このクラスはセッション情報をファイルシステムなどに永続化することはせず、
    常にオンメモリで情報を保持する。
    """
    
    def __init__(self, obj, key):
        self.__sessions = {}
        self.__expire = obj['expire']
        self.secret_key = key

    @property
    def expire(self):
        return self.__expire

    def create(self):
        u"""新しいセッション情報を生成する。
        """
        while 1:
            with RLock():
                key = self.create_id()
                if key not in self.__sessions:
                    break
        self.__sessions[key] = self.create_session(key)
        self._sweep()
        return self.__sessions[key].clone()

    def _sweep(self):
        now = time()
        d = []
        for k, v in self.__sessions.items():
            if (v.created + float(self.expire)) < now:
                d.append(k)
        for x in d:
            del self.__sessions[x]

    def save(self, session):
        pass

    def store(self, session):
        self.__sessions[session.key] = SessionInfoWrapper(session)

    def restore(self, session_key):
        session = self.__sessions.get(session_key, None)
        if session:
            return session
        else:
            return self.create()

    def delete(self, session_key):
        pass

