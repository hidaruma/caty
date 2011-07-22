#coding:utf-8
from caty.core.command import Builtin
from caty.util.path import join

name = 'test'
schema = ''

class ListTestFiles(Builtin):
    command_decl = u"""
    @[test] command list-testfiles [string] :: void -> [string*]
    reads testfiles
    refers python:caty.command.test.ListTestFiles;

    """
    def setup(self, path):
        self.path = path

    def execute(self):
        d = self.testfiles.DirectoryObject(self.path)
        r = []
        for e in d.read(True):
            if e.path.endswith('.json'):
                r.append(e.path)
        return r

class ReadTestFile(Builtin):
    command_decl = u"""
    @[test] command read-test [string] :: void -> string
    reads testfiles
    refers python:caty.command.test.ReadTestFile;

    """
    def setup(self, path):
        self.path = path

    def execute(self):
        f = self.testfiles.open(self.path)
        r = f.read()
        f.close()
        return r

from caty.jsontools import pp
class PP(Builtin):
    command_decl = u"""
    @[test] command pp :: any -> string
    refers python:caty.command.test.PP;
    """
    def execute(self, input):
        return pp(input)

class WriteFile(Builtin):
    command_decl = u"""
    @[test] command write-file [string] :: string -> void
    updates testfiles
    refers python:caty.command.test.WriteFile;
    """
    def setup(self, path):
        self.path = path

    def execute(self, input):
        f = self.testfiles.open(self.path, 'wb')
        f.write(input)
        f.close()

