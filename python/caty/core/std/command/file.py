#coding: utf-8
from __future__ import with_statement
from caty.core.command import Builtin
from caty.command import MafsMixin
from caty.jsontools import tagged
name = 'file'
schema = ''

class FileUtilMixin(MafsMixin):
    def setup(self, path):
        self.path = path

    def open(self, mode='rb'):
        return MafsMixin.open(self, self.path, mode)
    
    def opendir(self):
        return MafsMixin.opendir(self, self.path)

class ZeroFile(FileUtilMixin, Builtin):

    def execute(self):
        fo = self.open("rb") 
        # wモードだと即座に作られる、既存ファイルは書き込むまで切りつめされない
        if (fo.exists):
            fo.close()
            r = tagged(u'OK', fo.path)
        else:
            fo.close()
            fo = self.open("wb") # これだけで作られる。
            fo.close()
            r = tagged(u'OK', fo.path)
        return r

class Exists(FileUtilMixin, Builtin):

    def setup(self, opts, path):
        self.__pred = opts.pred
        FileUtilMixin.setup(self, path)
    
    def execute(self):
        fo = self.open()
        r = fo.exists
        fo.close()
        if self.__pred:
            return r
        if r:
            return tagged(u'OK', self.path)
        else:
            return tagged(u'NG', self.path)

class ReadFile(FileUtilMixin, Builtin):

    def execute(self):
        return self.open().read()
        
class ReadFileI(FileUtilMixin, Builtin):

    def setup(self, opts):
        self.dir = opts.dir

    def execute(self, input):
        self.path = input
        return self.open().read()

class WriteFile(FileUtilMixin, Builtin):

    def execute(self, input):
        with self.open('wb') as f:
            f.write(input)

class DeleteFile(FileUtilMixin, Builtin):

    def execute(self):
        p, m = self.parse_canonical_path(self.path)
        if m.is_dir(p):
            d = self.opendir()
            d.delete(True)
        else:
            f = self.open('wb')
            f.delete()


class LastModified(FileUtilMixin, Builtin):

    def execute(self):
        return unicode(self.open().last_modified)

class RealPath(FileUtilMixin, Builtin):

    def execute(self):
        return unicode(self.open().real_path)

class MakeDir(FileUtilMixin, Builtin):

    def execute(self):
        self.opendir().create()


