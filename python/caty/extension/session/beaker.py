from __future__ import absolute_import
#coding:utf-8
from caty.core.facility import Facility, AccessManager, DUAL
from caty.util import error_to_ustr
from beaker.middleware import SessionMiddleware
from beaker.session import Session, SessionObject, CookieSession
from beaker.util import coerce_session_params
class WSGISessionStorage(SessionObject):

    def _session(self):
        """Lazy initial creation of session object"""
        if self.__dict__['_sess'] is None:
            params = self.__dict__['_params']
            environ = self.__dict__['_environ']
            self.__dict__['_headers'] = req = {'cookie_out': None}
            req['cookie'] = environ.get('HTTP_COOKIE')
            if params.get('type') == 'cookie':
                self.__dict__['_sess'] = _CatySession(CookieSession)(req, **params)
            else:
                self.__dict__['_sess'] = _CatySession(Session)(req, use_cookies=True,
                                                 **params)
            self.__dict__['_sess'].storage = self
        return self.__dict__['_sess']

    def create(self):
        return self._session()

    def create_session(self, environ):
        return self.__class__(environ, self.__dict__['_params'])._session()

    def get_cookie_out(self):
        return self.__dict__['_headers']['cookie_out']

def _CatySession(Session):
    class WrappedSession(Session, Facility):
        am = AccessManager()
        def __init__(self, *args, **kwds):
            Facility.__init__(self, DUAL) # セッションが内部的にclearなどを使うため
            Session.__init__(self, *args, **kwds)

        def exists(self, key):
            return key in self
        
        @am.read
        def __getitem__(self, key):
            return Session.__getitem__(self, key)

        @am.read
        def get(self, key, default=None):
            return Session.get(self, key, default)

        @am.read
        def find(self, name, sjpath):
            u"""SJPath を用いて値を返す。
            """
            return self.__session.find(name, sjpath)

        @am.update
        def clear(self):
            u"""セッション変数をすべて削除する。
            """
            Session.clear(self)

        @am.update
        def put(self, k, v):
            Session.__setitem__(self, k, v)

        __setitem__ = put

        def merge_transaction(self, another):
            x.update(y)

        def commit(self):
            self.save()

        def clone(self):
            return self

        def update_time(self):
            self.__session.update_time()

        def to_name_tree(self):
            return {
                u'kind': u'ns:session',
                u'id': unicode(str(id(self))),
                u'childNodes': {}
            }
        
        def load(self):
            try:
                Session.load(self)
            except Exception as e: # beakerが一部の例外ハンドリングでunicodeエラーを引き起こす事が原因のworkaround
                if self.invalidate_corrupt:
                    util.warn(
                        "Invalidating corrupt session %s; "
                        "error was: %s.  Set invalidate_corrupt=False "
                        "to propagate this exception." % (self.id, error_to_ustr(e)))
                    self.invalidate()
                else:
                    raise
        
        def _to_dict(self):
            return {
                'key': self.id,
                'objects': self
            }
    return WrappedSession

def _ConsoleCatySession(Base):
    class WrappedConsoleSession(Base):
        def commit(self):
            self.storage.update_cookie_out()
            Base.commit(self)

        def cancel(self):
            self.storage.update_cookie_out()
            Base.cancel(self)
    return WrappedConsoleSession

class SessionStorage(WSGISessionStorage):
    def __init__(self, conf, environ=None):
        import os
        WSGISessionStorage.__init__(self, environ or os.environ, **coerce_session_params(conf))

    def update_cookie_out(self):
        self.__cookie_out = self.__dict__['_headers']['cookie_out']
        environ = self.__dict__['_environ']
        environ['HTTP_COOKIE'] = self.__cookie_out

    def _session(self):
        """Lazy initial creation of session object"""
        if self.__dict__['_sess'] is None:
            params = self.__dict__['_params']
            environ = self.__dict__['_environ']
            self.__dict__['_headers'] = req = {'cookie_out': None}
            req['cookie'] = environ.get('HTTP_COOKIE')
            if params.get('type') == 'cookie':
                self.__dict__['_sess'] = _ConsoleCatySession(_CatySession(CookieSession))(req, **params)
            else:
                self.__dict__['_sess'] = _ConsoleCatySession(_CatySession(Session))(req, use_cookies=True,
                                                 **params)
            self.__dict__['_sess'].storage = self
        return self.__dict__['_sess']

    def create_session(self, environ):
        return self.__class__(self.__dict__['_params'], environ)._session()

def convert_conf(conf):
    d = {}
    for k, v in conf.items():
        d['beaker.session.' + k] = v
    return d

class WSGISessionWrapper(SessionMiddleware):
    def __init__(self, wrap_app, config=None, environ_key='caty.session', **kwds):
        SessionMiddleware.__init__(self, wrap_app, convert_conf(config), environ_key, **kwds)

    def __call__(self, environ, start_response):
        session = WSGISessionStorage(environ, **self.options)
        if environ.get('paste.registry'):
            if environ['paste.registry'].reglist:
                environ['paste.registry'].register(self.session, session)
        environ[self.environ_key] = session
        environ['beaker.get_session'] = self._get_session

        if 'paste.testing_variables' in environ and 'webtest_varname' in self.options:
            environ['paste.testing_variables'][self.options['webtest_varname']] = session

        def session_start_response(status, headers, exc_info=None):
            if session.accessed():
                session.persist()
                if session.__dict__['_headers']['set_cookie']:
                    cookie = session.get_cookie_out()
                    if cookie:
                        headers.append(('Set-cookie', cookie))
            return start_response(status, headers, exc_info)
        return self.wrap_app(environ, session_start_response)

    start = __call__

