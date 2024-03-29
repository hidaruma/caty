#coding:utf-8
import caty.jsontools as json
import caty.jsontools.stdjson as stdjson
from caty.util import error_to_ustr
from caty.core.handler import WebInputParser
import threading
from wsgiref.simple_server import make_server, WSGIRequestHandler

class HTTPConsoleThread(threading.Thread):
    def __init__(self, system, port):
        import caty.front.web.simple as server_module
        from wsgiref.simple_server import WSGIRequestHandler
        threading.Thread.__init__(self)
        self.is_debug = True
        server_class = server_module.get_server(system, True)
        handler_class = HTTPConsoleRequestHandler
        dispatcher = HTTPConsoleApp(system, True)
        self.httpd = make_server('', 
                                 int(port), 
                                 dispatcher, 
                                 server_class, 
                                 handler_class)
        from caty.util import cout
        cout.writeln("HTTP console serving on port %s..." % port)
        self.port = port

    def run(self):
        self.httpd.serve_forever()

    def stop(self):
        self.httpd.server_close()

    def shutdown(self):
        self.httpd.shutdown()

    def status(self):
        return u'running on port %s' % self.port

class HTTPConsoleRequestHandler(WSGIRequestHandler):
    def get_environ(self):
        environ = WSGIRequestHandler.get_environ(self)
        content_type = environ.get('CONTENT_TYPE', 'text/plain')
        if content_type == 'text/plain':
            if 'HTTP_X_CATY_TARGET_APP' not in environ:
                environ['HTTP_X_CATY_TARGET_APP'] = u'root'
                for k, v in self.headers.items():
                    if k.lower() == 'x-caty-target-app':
                        environ['HTTP_X_CATY_TARGET_APP'] = v
        return environ

class HTTPConsoleApp(object):
    u"""
    HTTPコンソールのリクエストを受け取る
    """
    def __init__(self, system, is_debug):
        self._system = system
        self.is_debug = is_debug
        self._remove_app_rpc = system.remove_app
        self._setup_app_rpc = system.setup_app
    
    def set_remove_app_rpc(self, func):
        self._remove_app_rpc = func

    def set_setup_app_rpc(self, func):
        self._setup_app_rpc = func

    def __call__(self, environ, start_response):
        content_type = environ.get('CONTENT_TYPE', 'text/plain')
        if ';' in content_type:
            content_type, encoding = map(str.strip, content_type.split(';', 1))
        else:
            encoding = self._system.sysencoding
        if content_type == 'text/plain':
            app_name = environ.get('HTTP_X_CATY_TARGET_APP', 'root')
            input = WebInputParser(environ, encoding).read()
        else:
            try:
                req = json.untagged(WebInputParser(environ, encoding).read())
                if content_type != 'application/json':
                    for k, v in req.items():
                        req[k] = v[0]
                app_name = req.get('targetApp', 'root')
                input = req['script']
            except Exception, e:
                result = error_to_ustr(e)
                body = stdjson.dumps(result).encode('unicode-escape')
                status = '400 Bad Request'
                headers = {
                    'content-type': 'application/json',
                    'content-length': str(len(body))
                }
                start_response(status, headers.items())
                return [body]

        result, status = self._process(app_name, input, environ)
        if status.startswith('500 '):
            body = result
        else:
            body = stdjson.dump_bytes(result)
        headers = {
            'Content-type': 'application/json',
            'Content-length': str(len(body))
        }
        start_response(status, list(headers.items()))
        return [body]

    def _process(self, app_name, input, environ):
        if app_name == 'project':
            return self.system_function(input)
        app = self._system.get_app(app_name)
        facilities = app.create_facilities()
        app.init_env(facilities, True, [u'console'], self._system, environ)
        interpreter = facilities['interpreter']
        try:
            c = interpreter.build(input if isinstance(input, unicode) else unicode(input, app.sysencoding))
        except Exception, e:
            result = error_to_ustr(e)
            status = '400 Bad Request'
        else:
            try:
                result = c({})
                status = '200 OK'
            except:
                import traceback
                result = traceback.format_exc()
                status = '500 Internal Server Error'
        return result, status

    def system_function(self, input):
        chunk = input.split(' ')
        cmd = chunk.pop(0)
        if cmd == 'init-app':
            try:
                target = chunk.pop(0)
                result = True
                status = '200 OK'
            except Exception:
                result = False
                status = '400 Bad Request'
            else:
                self._setup_app_rpc(target)
        elif cmd == 'remove-app':
            try:
                target = chunk.pop(0)
                result = True
                status = '200 OK'
            except:
                result = False
                status = '400 Bad Request'
            else:
                self._remove_app_rpc(target)
        else:
            result = False
            status = '400 Bad Request'
        return result, status



