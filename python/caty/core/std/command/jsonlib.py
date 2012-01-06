#coding: utf-8
from caty.core.command import Builtin
from caty.core.exception import *
from caty.core.std.command.file import FileUtilMixin
from caty.util import error_to_ustr
import caty.jsontools as json
import caty.jsontools.xjson as xjson
import caty.jsontools.stdjson as stdjson


class ReadJson(FileUtilMixin, Builtin):
    def execute(self):
        f = self.open('rb')
        if not f.exists:
            raise FileNotFound(path=f.path)
        j = stdjson.load(f)
        f.close()
        return j

class WriteJson(FileUtilMixin, Builtin):
    def execute(self, input):
        f = self.open('wb')
        f.write(stdjson.dumps(input))
        f.close()

class Pretty(Builtin):
    def execute(self, input):
        return json.pp(input)

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
        try:
            return merge_dict(input[0], input[1], self.merge_mode)
        except:
            return None

class JsonResponse(Builtin):
    def setup(self, opts):
        self._status = opts['status']
        self._encoding = opts['encoding']

    def execute(self, input):
        out = stdjson.dumps(input, ensure_ascii=False)
        return {
            'status': self._status,
            'body': out,
            'header': {
                'content-type': u'application/json; charset=%s' % self._encoding,
            }
        }


class Parse(Builtin):
    def execute(self, input):
        return stdjson.loads(input)


class FixOnSelection(Builtin):
    def execute(self, input):
        fx = json.SelectionFixer(self.schema)
        return fx.fix(input)

