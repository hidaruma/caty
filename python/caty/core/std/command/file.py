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
        self.__pred = opts['pred']
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
        
class WriteFile(FileUtilMixin, Builtin):


    def setup(self, opts, path):
        FileUtilMixin.setup(self, path)
        self.__mkdir = opts['mkdir']

    def execute(self, input):
        with self.open('wb') as f:
            if self.__mkdir:
                for p in f.list_parents():
                    d = f.opener.opendir(p)
                    if not d.exists:
                        d.create()
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
    def setup(self, opts, path):
        FileUtilMixin.setup(self, path)
        self.__mkdir = opts['mkdir']

    def execute(self):
        f = self.opendir()
        if self.__mkdir:
            for p in f.list_parents():
                d = f.opener.opendir(p)
                if not d.exists:
                    d.create()
        f.create()

def namecmp(a, b):
    u"""FileObjectのソート用の比較関数。
    パス名を比較に用いる。
    """
    return cmp(a.path, b.path)

def fo_to_json(fo, long_format):
    if not long_format:
        return {u'name': fo.basename, u'isDir': fo.is_dir}
    else:
        return {
            u'name': fo.basename, 
            u'abspath': fo.path,
            u'isDir': fo.is_dir,
            u'lastModified': unicode(fo.last_modified) if not fo.is_dir else u''
            }



def has_ext(fo, ext):
    return fo.path.endswith(ext)

def kind_of(ent, kind):
    if kind == "file":
        return not ent.is_dir
    elif kind == "dir":
        return ent.is_dir
    else:
        return True

class LsDir(FileUtilMixin, Builtin):
    
    def setup(self, opts, path, glob=''):
        if not path.endswith('/'):
            path = path + '/'
        self.path = path
        self.glob = glob
        self.long_format = opts.get('long', False)
        self.rec = opts.get('rec', False)
        kind = opts.get('kind', None)
        self.kind = "file" if kind == "file" else ("dir" if kind == "dir"  else "any")

    def execute(self):
        from caty.util import bind2nd
        from caty.core.action.selector import PathMatchingAutomaton
        dirobj = self.opendir()
        if self.glob:
            if '*' not in self.glob:
                p = '*' + self.glob
            else:
                p = self.glob
            matcher = PathMatchingAutomaton(p)
        else:
            matcher = FakeMatcher()
        if not self.rec:
            entries = dirobj.read()
        else:
            entries = self.rec_read(dirobj)
        files = list(sorted([ent for ent in entries if matcher.match(ent.path) and kind_of(ent, self.kind)],
                            cmp=namecmp))
        r = map(bind2nd(fo_to_json, self.long_format), files)
        return r

    def rec_read(self, dirobj):
        for e in dirobj.read():
            yield e
            if e.is_dir:
                for e2 in self.rec_read(e):
                    yield e2

class FakeMatcher(object):
    def match(self, s):
        return True

