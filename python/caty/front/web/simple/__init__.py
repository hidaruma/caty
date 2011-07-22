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
            self.shutdown()

class ErrorLogWriter(object):
    def __init__(self, logger):
        self.logger = logger

    def write(self, msg):
        self.logger.error(msg)

    def flush(self):
        pass

class CatyRequestHandler(WSGIRequestHandler):
    def __init__(self, logger, request, client_address, server):
        self.__logger = logger
        self.__error_log_writer = ErrorLogWriter(logger)
        WSGIRequestHandler.__init__(self, request, client_address, server)

    def log_message(self, format, *args):
        self.__logger.info("%s - - [%s] %s" %
                         (self.address_string(),
                          self.log_date_time_string(),
                          format%args))
    def get_stderr(self):
        return self.__error_log_writer


def get_server(*args):
    return CatyWSGIServer

def get_handler(system, is_debug):
    logger = system.access_logger
    return lambda r, c, s: CatyRequestHandler(logger, r, c, s)

from caty.front.web.app import CatyWSGIDispatcher
def get_dispatcher(system, is_debug):
    return CatyWSGIDispatcher(system, is_debug)

