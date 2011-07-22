#coding: utf-8
from caty.core.command import Builtin
from caty.core.exception import *
name='http'
schema=''
class Found(Builtin):
    command_decl = u"""
    /**
     * 与えられたパスに対しての302 Foundレスポンスを出力する。
     */
    command found [string] :: void -> Response
        refers python:caty.command.http.Found;
    """

    def setup(self, path):
        self._path = path

    def execute(self):

        return {
            'status': 302,
            'body': u'',
            'header': {
                'Location': self._path
            }
        }

class Forbidden(Builtin):
    command_decl = u"""
    /**
     * 与えられたパスに対しての403 Forbiddenを出力する。
     */
    command forbidden [string] :: void -> never
        refers python:caty.command.http.Forbidden;
    """
    def setup(self, path):
        self._path = path

    def execute(self):
        raise CatyException(
            'HTTP_403',
            u'Can not access to $path',
            path=self._path
        )

class NotFound(Builtin):
    command_decl = u"""
    /**
     * 与えられたパスに対しての404 Forbiddenを出力する。
     */
    command not-found [string] :: void -> never
        refers python:caty.command.http.NotFound;
    """
    def setup(self, path):
        self._path = path

    def execute(self):
        raise CatyException(
            'HTTP_404', 
            u'File does not exists: $path',
            path=self._path
            )


class BadRequest(Builtin):
    command_decl = u"""
    /**
     * 与えられたパスに対しての400 Bad Requestを出力する。
     */
    command bad-request [string path, string method] :: void -> never
        refers python:caty.command.http.BadRequest;
    """
    def setup(self, path, method):
        self._path = path
        self._method = method

    def execute(self):
        raise CatyException(
            'HTTP_400', 
            u'Bad Access: path=$path, method=$method',
            path=self._path,
            method=self._method
            )

class NotAllowed(Builtin):
    command_decl = u"""
    /**
     * 与えられたパスに対しての405 Method Not Allowedを出力する。
     */
    command not-allowed [string path, string method] :: void -> never
        refers python:caty.command.http.NotAllowed;
    """
    def setup(self, path, method):
        self._path = path

    def execute(self):
        raise CatyException(
            'HTTP_405', 
            u'HTTP method `$mthod` is not allowed for `$path`',
            path=self._path
            )



