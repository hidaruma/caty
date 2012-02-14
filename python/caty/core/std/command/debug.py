#coding: utf-8
from caty.core.command import Builtin
from caty.core.schema import *
from caty.command import *
from caty.util import cout
import caty.jsontools as json
import caty
name = u'debug'
schema = u''
class Dump(Builtin):
    def setup(self, opts):
        self._force = opts['force']
        self._prefix = opts['prefix']

    def execute(self, input):
        e = self.env.get('SYSTEM_ENCODING')
        if self.env.get('DEBUG') or self._force:
            r = json.prettyprint(input).encode(e)
            if self._prefix:
                r = self._prefix.encode(e) + ' ' + r
            print r
        return input

class DumpSession(Builtin):

    def execute(self):
        return self.session._to_dict()['objects']

class GetSession(Builtin):

    def setup(self, opts, key):
        self.__key = key
        self.__nullable = opts.get('nullable', caty.UNDEFINED)

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
        self.tree = opts.get('tree', caty.UNDEFINED)

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


class Fuser(Builtin):
    def execute(self):
        import os
        ref = {}
        pid = os.getpid()
        d = u"/proc/%d/fd/" % pid
        try:
            for fd in os.listdir(d):
                f = os.readlink(d+fd)
                if f not in ref:
                    ref[f] = 1
                else:
                    ref[f] += 1
        except OSError:
            pass
        i = 0
        for k, v in ref.items():
            i += v
        ref[u"total"] = i
        return ref


class Annotate(Builtin, MafsMixin):
    def setup(self, path):
        self._path = path
        if not self._path.startswith('/'):
            self._path = 'scripts@this:/' + self._path

    def execute(self):
        from copy import deepcopy
        from caty.core.script.annotation import ScriptAnnotation
        from caty.core.script import PEND
        cmd = self.interpreter.build(self.open(self._path).read(),
                                     [], 
                                     [], 
                                     transaction=None)
        r = ScriptAnnotation().visit(cmd.cmd)
        return u''.join(r)
