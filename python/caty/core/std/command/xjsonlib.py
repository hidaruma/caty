# coding: utf-8
from caty.core.command import Builtin
from caty.core.exception import *
from caty.core.std.command.file import FileUtilMixin
import caty.jsontools as json
import caty.jsontools.xjson as xjson
import caty.jsontools.dxjson as dxjson
import caty.jsontools.stdjson as stdjson
import caty.jsontools.selector as selector

name = 'xjson'
schema = u"""
type AnyObject = {*:any};
"""

class ReadJson(FileUtilMixin, Builtin):
    def setup(self, opts, path):
        FileUtilMixin.setup(self, path)
        self.__with_doc = opts.with_doc

    def execute(self):
        f = self.open('rb')
        if not f.exists:
            raise FileNotFound(path=f.path)
        if self.__with_doc:
            j = dxjson.loads(f.read())
        else:
            j = xjson.loads(f.read())
        f.close()
        return json.decode(j)
        

class WriteJson(FileUtilMixin, Builtin):
    def setup(self, opts, path):
        FileUtilMixin.setup(self, path)
        self._json = opts.encode_json

    def execute(self, input):
        f = self.open('wb')
        if not self._json:
            e = xjson.dumps(input)
        else:
            e = stdjson.dump(json.encode(input))
        f.write(e)
        f.close()


class Parse(Builtin):
    def execute(self, input):
        return xjson.loads(input)

class Encode(Builtin):
    def execute(self, input):
        return json.encode(input)

class Select(Builtin):
    def setup(self, opts, pathexp):
        self._pathexp = pathexp
        self._strict = opts['strict']

    def execute(self, input):
        stm = selector.compile(self._pathexp, not self._strict)
        return list(stm.select(input))

class ToXML(Builtin):
    def execute(self, input):
        return xjson.toxml(input)

class Put(Builtin):
    def setup(self, opts, pathexp):
        self._pathexp = pathexp
        self._allow_loose = opts.allow_loose

    def execute(self, input):
        src, value = input
        stm = selector.compile(self._pathexp)
        return stm.replace(src, value, self._allow_loose)

class Get(Builtin):
    def setup(self, opts, pathexp):
        self._pathexp = pathexp.rstrip('?')
        self._safe = opts.safe or pathexp.endswith('?')
        self._default = opts.default

    def execute(self, input):
        from caty import UNDEFINED
        stm = selector.compile(self._pathexp)
        try:
            return stm.select(input).next()
        except:
            if self._default != UNDEFINED:
                return self._default
            if not self._safe:
                raise
            else:
                import caty
                return caty.UNDEFINED
