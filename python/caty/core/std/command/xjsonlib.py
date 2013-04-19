# coding: utf-8
from caty.core.command import Builtin
from caty.core.exception import *
from caty.core.std.command.file import FileUtilMixin
import caty.jsontools as json
import caty.jsontools.xjson as xjson
import caty.jsontools.dxjson as dxjson
import caty.jsontools.stdjson as stdjson
import caty.jsontools.selector as selector

class ReadJson(FileUtilMixin, Builtin):
    def setup(self, opts, path):
        FileUtilMixin.setup(self, path)
        self.__with_doc = opts['with-doc']

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
        self._json = opts['encode-json']

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

class ToJson(Builtin):
    def execute(self, input):
        return json.encode(json.normalize(input))


class FromJson(Builtin):
    def execute(self, input):
        return json.decode(input)


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
        self._allow_loose = opts['allow-loose']

    def execute(self, input):
        src, value = input
        stm = selector.compile(self._pathexp)
        return stm.replace(src, value, self._allow_loose)

import caty
class Get(Builtin):
    def setup(self, opts, pathexp=u'$'):
        self._pathexp = pathexp
        self._safe = opts['safe']
        self._default = opts.get('default', caty.UNDEFINED)

    def execute(self, input):
        from caty.jsontools.selector.stm import Nothing
        stm = selector.compile(self._pathexp)
        if self._safe:
            stm.set_optional(self._safe)
        if self._default != caty.UNDEFINED:
            stm.set_optional(True)
            stm.set_default(self._default)
        try:
            r = stm.select(input).next()
            return r
        except (KeyError, Nothing) as e:
            if not self._safe:
                msg = '{0} Line {1}, Col {2}'.format(self._pathexp, self.line, self.col)
                throw_caty_exception(u'Undefined', msg)
            else:
                return caty.UNDEFINED

class Pretty(Builtin):
    def execute(self, input):
        return json.pp(input)

class Flatten(Builtin):
    def setup(self, opts):
        self.rec = opts['rec']
        self.object = opts['also-obj']

    def execute(self, obj):
        if isinstance(obj, json.TaggedValue):
            t, o = json.split_tag(obj)
            return json.tagged(t, self.flatten(o))
        else:
            return self.flatten(obj)

    def flatten(self, obj, depth=0):
        r = []
        if depth > 1 and not self.rec:
            return [obj]
        if isinstance(obj, dict):
            if self.object:
                for v in obj.values():
                    r.extend(self.flatten(v, depth+1))
            else:
                r.append(obj)
        elif isinstance(obj, list):
            for v in obj:
                r.extend(self.flatten(v, depth+1))
        else:
            r.append(obj)
        return r

class Normalize(Builtin):
    def execute(self, data):
        return json.normalize(data)

from caty.util.collection import merge_dict
class Merge(Builtin):
    def setup(self, opts):
        if not opts['mode']:
            self.merge_mode = 'pre'
        else:
            if opts['mode'] == 'fst':
                self.merge_mode = 'pre'
            elif opts['mode'] == 'snd':
                self.merge_mode = 'post'
            else:
                self.merge_mode = 'error'

    def execute(self, input):
        if input == []:
            return {}
        f = lambda a, b: merge_dict(a, b, self.merge_mode)
        try:
            return reduce(f, input)
        except:
            return None

class ReadDir(Builtin):
    def setup(self, path):
        self.path = path

    def execute(self):
        r = {}
        for dirent in self.pub.opendir(self.path).read():
            if dirent.path.endswith('.xjson') and not dirent.is_dir:
                r[dirent.basename.split('.')[0]] = xjson.loads(dirent.read())
        return r

