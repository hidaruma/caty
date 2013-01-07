# coding: utf-8
from __future__ import with_statement
from caty.session.value import SessionInfo, SessionInfoWrapper
from caty.session.base import SessionStorageBase
from caty.jsontools import json
from caty.jsontools.path import build_query
from threading import RLock
from hashlib import sha1
from time import time
import random
import sys

class SessionStorage(SessionStorageBase):
    u"""セッションデータ一覧を保持し、セッション情報の取得と永続化を行う。
    このクラスはセッション情報をファイルシステムなどに永続化することはせず、
    常にオンメモリで情報を保持する。
    """
    
    def __init__(self, obj):
        self.__sessions = {}
        self.__expire = obj['expire']

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

    def create_session(self, environ):
        session = None
        if 'HTTP_COOKIE' in environ:
            c = environ['HTTP_COOKIE']
            cookie = SimpleCookie()
            cookie.load(c)
            if 'sessionid' in cookie:
                session = self.restore(cookie['sessionid'].value)
        if session == None:
            session = SessionInfoWrapper(SessionInfo('session_scope', self))
        return session

from Cookie import SimpleCookie, Morsel
from caty.session.value import create_variable, SessionInfo, SessionInfoWrapper
class WSGISessionWrapper(object):
    def __init__(self, dispatcher, opts):
        self.dispatcher = dispatcher
        self.opts = opts

    def __call__(self, environ, start_response):
        try:
            def session_start_response(status, headers, exc_info=None):
                cookie = self._extend_cookie(environ) 
                if cookie:
                    headers.append(('Set-Cookie', cookie))
                return start_response(status, headers, exc_info)
            environ['caty.session'] = self.dispatcher._system._global_config.session.storage.create_session(environ)
            return self.dispatcher(environ, session_start_response)
        except:
            import traceback
            traceback.print_exc()
            raise

    def _extend_cookie(self, environ):
        if 'HTTP_COOKIE' in environ:
            c = environ['HTTP_COOKIE']
            cookie = SimpleCookie()
            cookie.load(c)
            if 'sessionid' in cookie:
                session = self.dispatcher._system._global_config.session.storage.restore(cookie['sessionid'].value)
                session.create(u'updates').update_time()
            else:
                return ''
        else:
            return ''
        m = Morsel()
        m.set('sessionid', session.key, session.key)
        m['expires'] = session.storage.expire
        m['path'] = '/'
        return m.OutputString()


def convert_conf(cfg):
    return cfg

