import socket
from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler
from SocketServer import *
import sys


class CatyWSGIServer(ThreadingMixIn, WSGIServer):
    __python_version = float(sys.version.split(' ')[0].rsplit('.', 1)[0])
    if __python_version <= 2.5:
        def serve_forever(self):
            self.__wait = True
            while self.__wait:
                self.handle_request()

    if __python_version <= 2.5:
        def server_close(self):
            self.__wait = False
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(('127.0.0.1', self.server_port))
            client.send('')
            client.close()
            WSGIServer.server_close(self)
    else:
        def server_close(self):
            WSGIServer.server_close(self)

class ErrorLogWriter(object):
    def __init__(self, logger):
        self.logger = logger

    def write(self, msg):
        self.logger.error(msg)

    def flush(self):
        pass

class CatyRequestHandler(object):
    def __init__(self, logger):
        self.__logger = logger
        self.__error_log_writer = ErrorLogWriter(logger)

    def log_message(self, format, *args):
        self.__logger.info("%s - - [%s] %s" %
                         (self.address_string(),
                          self.log_date_time_string(),
                          format%args))

    def get_stderr(self):
        return self.__error_log_writer

    def process_env(self, env):
        return env

def get_server(*args):
    return CatyWSGIServer

def make_handler(handler_class, base_class=WSGIRequestHandler):
    class _Handler(handler_class, base_class):
        def __init__(self, r, c, s, *rest):
            handler_class.__init__(self, *rest)
            base_class.__init__(self, r, c, s)

        def get_environ(self):
            e = base_class.get_environ(self)
            return handler_class.process_env(self, e)

    return _Handler

def get_handler_class():
    return CatyRequestHandler

def get_handler(system, is_debug):
    logger = system.access_logger
    rh_class = make_handler(get_handler_class())
    return lambda r, c, s: rh_class(r, c, s, logger)

from caty.front.web.app import CatyWSGIDispatcher, CatyApp
def get_dispatcher(system, is_debug):
    return CatyWSGIDispatcher(system, is_debug)

def get_app_class():
    return CatyApp

def get_performer(system, is_debug):
    return CatyWSGIPerformerDispatcher(system, is_debug)

class CatyWSGIPerformerDispatcher(CatyWSGIDispatcher):
    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        app = self.dispatch(path)
        return CatyPerformer(app, self.is_debug, self._system).start(environ, start_response)

from caty.core.performer import PerformerRequestHandler
class CatyPerformer(CatyApp):
    def get_request_handler_class(self):
        return PerformerRequestHandler

