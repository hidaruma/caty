#coding: utf-8
from caty.core.command import Builtin


class _Log(Builtin):
    def setup(self, opts):
        self.__cout = opts['cout']

    def execute(self, string):
        self._write(string)
        if self.__cout:
            self.stream.write(string)
            self.stream.write('\n')

class Debug(_Log):
    def _write(self, msg):
        self.logger.app_log.debug(msg)

class Info(_Log):
    def _write(self, msg):
        self.logger.app_log.info(msg)

class Warning(_Log):
    def _write(self, msg):
        self.logger.app_log.warning(msg)

class Error(_Log):
    def _write(self, msg):
        self.logger.app_log.error(msg)

