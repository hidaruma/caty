#coding: utf-8
from caty.core.command import Builtin
from caty.core.schema import *
from caty.util import cout
name = u'debug'
schema = u''
class Dump(Builtin):
    command_decl = u"""
        /**
         * 入力値を標準出力に書き出す。それ以外の動作は pass と同じ。
         */
        command dump<T> :: T -> T
            refers python:caty.command.debug.Dump;
    """
    def execute(self, input):
        print input
        return input

class DumpSession(Builtin):
    command_decl = u"""
    /**
     * セッションの値をすべて出力する。
     */
     command dump-session :: void -> object
        reads session
        refers python:caty.command.debug.DumpSession;
    """
    def execute(self):
        return self.session._to_dict()['objects']

class GetSession(Builtin):
    command_decl = u"""
    /**
     * セッションから指定されたキーの値を取得する。
     * nullable オプションが指定された場合、キーが見つからなかったときに null を返す。
     */
     command get-session<T> {"nullable": boolean} [string] :: void -> T
        reads session
        refers python:caty.command.debug.GetSession;
    """
    def setup(self, opts, key):
        self.__key = key
        self.__nullable = opts.nullable

    def execute(self):
        try:
            return self.session._to_dict()['objects'][self.__key]
        except:
            if self.__nullable:
                return None
            else:
                raise

from caty.core.casm.cursor import TreeDumper
class DumpSchema(Builtin):
    command_decl = u"""
    /**
     * スキーマ定義のダンプ
     */
    command dump-schema [string] :: void -> void
        reads schema
        refers python:caty.command.debug.DumpSchema;
    """
    def setup(self, name):
        self.__schema_name = name

    def execute(self):
        print TreeDumper().visit(self.schema[self.__schema_name])

class Profile(Builtin):
    command_decl = u"""
    /**
     * メモリ使用状況のプロファイルを行う。
     * このコマンドを使うにはguppy (http://pypi.python.org/pypi/guppy)が必要となる。
     */
    command profile {"tree": boolean} :: void -> string
        refers python:caty.command.debug.Profile;
    """
    def setup(self, opts):
        self.tree = opts.tree

    def execute(self):
        try:
            from guppy import hpy
        except:
            print self.i18n.get(u'guppy is required but not installed')
            return u''
        else:
            h = hpy()
            if self.tree:
                p = h.heap().get_rp()
            else:
                p = h.heap()
            return unicode(str(p))


