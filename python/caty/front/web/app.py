# coding: utf-8
u"""Caty の Web フロントエンド。
"""
from copy import deepcopy
from Cookie import SimpleCookie, Morsel
import wsgiref
import cgi
import sys
import os
import time
from wsgiref.simple_server import make_server, WSGIRequestHandler
import traceback

import caty
import caty.jsontools as json
import caty.jsontools.xjson as xjson
from caty.jsontools import jstypes
from caty.session.value import create_variable, SessionInfo, SessionInfoWrapper
from caty.core.command.exception import *
from caty.util import error_to_ustr
from caty.util.path import join
from caty.util.web import HTTP_STATUS
from caty.core.handler import AppDispatcher, RequestHandler

class CatyWSGIDispatcher(AppDispatcher):
    u"""
    Caty アプリケーションの WSGI に対するフロントエンド。
    リクエストされたパスに応じてアプリケーションを振り分ける。
    """
    def __init__(self, system, is_debug):
        self._system = system
        self.is_debug = is_debug
        AppDispatcher.__init__(self, system)

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        app = self.dispatch(path)
        return CatyApp(app, self.is_debug, self._system).start(environ, start_response)


class CatyApp(object):
    def __init__(self, site, is_debug, system):
        self._app = site
        self.is_debug = is_debug
        self._system = system
        self.addrsAllowed = system.addrsAllowed
        self.addrsDenied = system.addrsDenied

    def start(self, environ, start_response):
        if self._ip_address_denied(environ):
            j = self.error_403(None, environ)
            h = list(self.create_header(j['header']))
        else:
            j, h = self._start_proc(environ)
        return self._end_proc(j, h, start_response)

    def _ip_address_denied(self, environ):
        ip = environ['REMOTE_ADDR']
        for deny in self.addrsDenied:
            if deny.endswith('*'):
                if ip.rsplit('.', 1)[0] == deny.rsplit('.', 1)[0]:
                    return True
            elif ip == deny:
                return True
        
        if self.addrsAllowed is not None:
            for allow in self.addrsAllowed:
                if allow.endswith('*'):
                    if ip.rsplit('.', 1)[0] == allow.rsplit('.', 1)[0]:
                        return False
                elif ip == allow:
                    return False
            return True
        return False

    def _start_proc(self, environ):
        try:
            json = self.main(environ)
            self._format_linebreak(json)
            headers = list(self.create_header(json['header']))
            if 'Set-Cookie' not in json['header']:
                cookie = self._extend_cookie(environ) 
            else:
                cookie = ''
            if cookie:
                headers.append(('Set-Cookie', cookie))
        except Exception, e:
            print traceback.format_exc()
            print e
            return {}, list(self.create_header({'status': 500}))
        return json, headers

    def _end_proc(self, json, headers, start_response):
        status = 200
        status = HTTP_STATUS[json.get('status', 200)]
        start_response(status, headers)
        if 'body' in json:
            b = json['body']
            if isinstance(b, unicode):
                b = b.encode(json.get('encoding', 'utf-8'))
            return [b]
        else:
            return []

    def _format_linebreak(self, j):
        tp = j.get('header', {}).get('content-type', '')
        s = j.get('body', u'')
        if tp.startswith('text/plain'):
            j['body'] = s.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
            j['header']['content-length'] = len(j['body'].encode(j.get('encoding', 'utf-8')))

    def main(self, environ):
        path = environ['PATH_INFO']
        query = self._get_query(environ)
        raw_input = environ['wsgi.input'].read(int(environ['CONTENT_LENGTH'] or 0))
        input, options, method, environ = self._process_env(raw_input, query, environ)
        
        if method not in (u'POST', u'PUT'):
            input = None
        facilities = self._app.create_facilities(lambda : self.create_session(environ))
        del environ['PATH_INFO'] # init_envで生PATH_INFOを使わせない
        self._app.init_env(facilities, self.is_debug, [u'web'], self._system, environ)
        handler = RequestHandler(facilities['interpreter'], 
                                 facilities['env'],
                                 self._app)
                                 #self._app.pub, 
                                 #self._app.web_config, 
                                 #self._app.encoding)
        r = handler.request(path, options, method, input)
        environ['PATH_INFO'] = path
        return r
        #cmd = handler.request(path, options, method)
        #r = cmd(input)
        #return r

    def _get_query(self, environ):
        qs = environ['QUERY_STRING']
        d = {}
        for k, v in cgi.parse_qs(qs).items():
            d[k] = unicode(v[0], self._app.encoding)
        method = environ['REQUEST_METHOD']
        return d

    def _process_env(self, raw_input, query, environ):
        from StringIO import StringIO
        new_env = {}
        new_env.update(environ)
        method = environ['REQUEST_METHOD']
        if '_method' in query and self._system.enable_http_method_tunneling:
            raw_input =  WebInputParser(environ, self._app.encoding).read()
            method = query['_method']
            del query['_method']
            for k, v in raw_input.items():
                if k.startswith('header.'):
                    new_env[k.replace('header.', '').replace('-', '_').upper()] = v[0]
            body = raw_input.get('body', [u''])[0].encode(self._app.encoding)
            new_env['wsgi.input'] = StringIO(body)
            new_env['REQUEST_METHOD'] = method
            input = body
        else:
            new_env = environ
            input = raw_input
        return input, query, method, new_env
                
    def _process_input(self, input, tp):
        if tp.startswith('application/json'):
            return json.tagged(u'json', xjson.loads(input))
        elif tp.startswith('text/plain'):
            return input
        else:
            return input

    def create_header(self, h):
        for k, v in h.iteritems():
            if isinstance(v, unicode):
                yield str(k), v.encode('utf-8')
            else:
                yield str(k), str(v)

    def create_session(self, environ):
        session = None
        if 'HTTP_COOKIE' in environ:
            c = environ['HTTP_COOKIE']
            cookie = SimpleCookie()
            cookie.load(c)
            if 'sessionid' in cookie:
                session = self._app.session_storage.restore(cookie['sessionid'].value)
        if session == None:
            session = SessionInfoWrapper(SessionInfo('session_scope', self._app.session_storage))
        return session

    def error_500(self, e, env):
        msg = u'500 Internal Server Error'
        tb = unicode(traceback.format_exc(), 'utf-8')
        print tb.encode(self._app.sysencoding)
        msg = error_to_ustr(e)
        print msg.encode(self._app.sysencoding)
        if self.is_debug:
            json['body'] = '<pre>%s</pre>' % tb.encode(self._app.sysencoding)
            json['header'] = {
                'content-type': 'text/html'
            }
        else:
            json = self.read_error_page('500.html', e, env, msg)
        json['status'] = 500
        return json

    def error_404(self, e, env):
        msg = u'404 Not Found'
        cmd = self.read_error_page('404.html', e, env, msg)
        json = cmd({'path': e.path})
        json['status'] = 404
        return json

    def error_403(self, e, env):
        msg = u'403 Forbidden'
        json = {
            'status': 403,
            'header': {
                'content-type': 'text/html'
            },
            'body': """
<title>403 Forbidden</title>
<h1>403 Forbidden</h1>
<p>%s</p>
            """ % (env['PATH_INFO'])
        }
        return json

    def read_error_page(self, path, e, env, msg):
        u = self._app.include.create(u'reads')
        c = self._app.common_files.include.create(u'reads')
        f = u.open('/'+path)
        if f.exists:
            return self.create_command(env, path, e.path)
        else:
            f = c.open('/framework_'+path)
            if f.exists:
                return self.create_command(env, f.path, e.path)
            else:
                return {
                    'body': u'''<title>%s</title>
                <h1>%s</h1>
                ''' % (msg, msg),
                    'header': {
                        'content-type': 'text/html'
                    }
                }

    def _extend_cookie(self, environ):
        if 'HTTP_COOKIE' in environ:
            c = environ['HTTP_COOKIE']
            cookie = SimpleCookie()
            cookie.load(c)
            if 'sessionid' in cookie:
                session = self._app.session_storage.restore(cookie['sessionid'].value)
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

class NotFound(Exception):
    def __init__(self, path):
        Exception.__init__(self, path)
        self.path = path
    
