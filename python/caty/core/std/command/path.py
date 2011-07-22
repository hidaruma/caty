#coding: utf-8
from caty.core.command import Builtin, Internal
from caty.util.path import join, split, splitext, dirname

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


