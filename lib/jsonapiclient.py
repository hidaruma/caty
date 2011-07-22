import urllib2
import json
import cookielib

class JSONMessenger(object):
    def __init__(self, host, app, userid, password, debug=False):
        self.host = host
        self.app = app
        self.userid = userid
        self.password = password
        opener = urllib2.OpenerDirector()
        classes = [urllib2.ProxyHandler,
               urllib2.UnknownHandler, 
               urllib2.HTTPHandler,
               urllib2.HTTPDefaultErrorHandler, 
               urllib2.HTTPRedirectHandler,
               urllib2.FTPHandler, 
               urllib2.FileHandler, 
               urllib2.HTTPCookieProcessor,
               MyHTTPErrorProcessor]
        for c in classes:
            opener.add_handler(c())
        self.opener = opener
        self.debug = debug

    def __getattr__(self, name):
        method, verb = name.split('_')
        return lambda path, input=None: self._request(path, input, verb, method)

    def _request(self, path, input=None, verb='', method='GET', fail_if_error=False):
        url = self.host + self.app + path
        if verb:
            url += '?_verb=%s' % verb
        req = RequestWithMethod(url)
        if self.debug:
            print method.upper()+':', url
        if input:
            data = json.dumps(input, ensure_ascii=False).encode('utf-8')
            req.data = data
            req.add_header('Content-Type', 'application/json')
            req.add_header('Content-Length', len(data))
        req.set_method(method.upper())
        uo = self.opener.open(req)
        meta = uo.info()
        if meta['content-type'].startswith('application/json'):
            obj = json.loads(uo.read())
            if obj == False:
                if fail_if_error:
                    raise Exception('!!!!')
                self._request('/', {'userid': self.userid, 'password': self.password}, 'login', 'POST')
                return self._request(path, input, verb, method, True)
            elif obj is None:
                raise Exception('error')
            else:
                return obj
        else:
            return 

class RequestWithMethod(urllib2.Request):
    def get_method(self):
        return self._method

    def set_method(self, method):
        self._method = method

class MyHTTPErrorProcessor(urllib2.BaseHandler):
    handler_order = 999

    def http_response(self, request, response):
        code, msg, hdrs = response.code, response.msg, response.info()
        if int(code / 100) != 2:
            response = self.parent.error(
                'http', request, response, code, msg, hdrs)
        return response
    https_response = http_response


