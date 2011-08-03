#coding: utf-8
from caty.core.command import Builtin
from caty.core.schema import *
from caty.util import cout
name = u'debug'
schema = u''
class Dump(Builtin):

    def execute(self, input):
        print input
        return input

class DumpSession(Builtin):

    def execute(self):
        return self.session._to_dict()['objects']

class GetSession(Builtin):

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

    def setup(self, name):
        self.__schema_name = name

    def execute(self):
        print TreeDumper().visit(self.schema[self.__schema_name])

class Profile(Builtin):

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


