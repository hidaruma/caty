#coding: utf-8
from caty.core.command import Builtin, Internal
from caty.util.path import join, split, splitext, dirname
import caty.jsontools as json

class Join(Builtin):
    def execute(self, path_list):
        return join(*path_list)



class Split(Builtin):
    def execute(self, path):
        return split(path)

class Dir(Builtin):
    def execute(self, path):
        return split(path)[0]

class Base(Builtin):
    def execute(self, path):
        return split(path)[1]

class Ext(Builtin):
    def execute(self, path):
        return splitext(path)[-1]

class Trunk(Builtin):
    def execute(self, path):
        return splitext(split(path)[-1])[0]

class ReplaceExt(Builtin):
    def execute(self, pair):
        path, ext = pair
        base = splitext(path)[0]
        return base + ext

class Matches(Builtin):
    def setup(self, opts, pattern):
        self._bool = opts['boolean']
        self._pattern = pattern

    def execute(self, path):
        from caty.core.action.selector import PathMatchingAutomaton
        from caty.core.action.resource import split_url_pattern
        for p in split_url_pattern(self._pattern):
            pma = PathMatchingAutomaton(p)
            if pma.match(path):
                if self._bool:
                    return True
                else:
                    return json.tagged(u'True', path)
        else:
            if self._bool:
                return False
            else:
                return json.tagged(u'False', path)
