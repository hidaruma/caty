# coding: utf-8
import time
from google.appengine.ext import db

def parent_dirs(path):
    u"""/a/b/c/d というパスから [/a, /a/b, /a/b/c] というパスのリストを返す。
    """
    parent, basename = path.rsplit('/', 1)
    if parent:
        for p in parent_dirs(parent):
            yield p
        yield parent

class EntitySizeLimitViolation(Exception):
    u"""1MB を越えるサイズのデータを StaticFile に設定しようとすると発生する。
    """
    pass

class StaticFile(db.Model):
    u"""静的ファイルオブジェクト。
    """
    path = db.StringProperty(required=True)
    mtime = db.FloatProperty(required=False)
    data = db.BlobProperty(required=False)
    parent_directory = db.ReferenceProperty(required=False)

    def __init__(self, *args, **kwds):
        db.Model.__init__(self, *args, **kwds)
        self.mtime = time.time()

    def create(self, contents=''):
        old = StaticFile.gql('where path = :1', self.path).get()
        if old: old.delete()
        old = ChunkFile.gql('where path = :1', self.path).get()
        if old: old.delete()
        dirs = list(parent_dirs(self.path))
        for d in dirs:
            if not StaticDirectory.gql('where path = :1', d).get():
                raise IOError(errno.ENOENT, os.strerror(errno.ENOENT) + (" '%s'" % d))
        self.mtime = time.time()
        self.data = db.Blob(str(contents))
        self.parent_directory = StaticDirectory().gql('where path = :1', dirs[-1]).get() if dirs else ROOT
        return self.put()

    def put(self, *args, **kwds):
        if len(str(self.data)) > 1000000:
            raise EntitySizeLimitViolation
        return db.Model.put(self, *args, **kwds)

    def read(self):
        return self.data

    def write(self, contents):
        self.data = db.Blob(str(contents))
        self.mtime = time.time()
        return self.put()
    
    @property
    def is_dir(self):
        return False

class Fragment(db.Model):
    u"""巨大ファイルの断片オブジェクト。
    パス情報は一切持たず、データの断片のみを持つ。
    """
    data = db.BlobProperty(required=True)

class ChunkFile(db.Model):
    u"""容量が1MBを越えるファイルの保存に利用する。
    """
    path = db.StringProperty(required=True)
    mtime = db.FloatProperty(required=False)
    parent_directory = db.StringProperty(required=False)
    fragments = db.ListProperty(db.Key)

    def create(self, contents=''):
        old = StaticFile.gql('where path = :1', self.path).get()
        if old: old.delete()
        old = ChunkFile.gql('where path = :1', self.path).get()
        if old: old.delete()
        dirs = list(parent_dirs(self.path))
        for d in dirs:
            if not StaticDirectory.gql('where path = :1', d).get():
                raise IOError(errno.ENOENT, os.strerror(errno.ENOENT) + (" '%s'" % d))
        self.mtime = time.time()
        self.parent_directory = StaticDirectory().gql('where path = :1', dirs[-1]).get() if dirs else ROOT
        self._create_fragment(contents)
        return self.put()

    def _create_fragment(self, contents):
        bytes = str(contents)
        data_range = range(len(bytes))
        l = []
        for offset in data_range[0:-1:1000000]:
            frag = bytes[offset:offset+1000000]
            child = Fragment(data=db.Blob(frag))
            k = child.put()
            l.append(k)
        self.fragments = l

    def write(self, contents):
        u"""更新処理。
        一旦すべてのフラグメントを削除してから更新を行う。
        低速だが確実。
        """
        for c in self.fragments:
            Fragment.get(c).delete()
        self._create_fragment(contents)
        self.mtime = time.time()
        return self.put()
    
    def read(self):
        return ''.join((Fragment.get(c).data for c in self.fragments))

    def delete(self):
        for c in self.fragments:
            Fragment.get(c).delete()
        db.Model.delete(self)

    @property
    def is_dir(self):
        return False

class StaticDirectory(db.Model):
    path = db.StringProperty(required=True)
    mtime = db.FloatProperty(required=False)
    parent_directory = db.StringProperty(required=False)
    
    def create(self):
        dirs = list(parent_dirs(self.path))
        for d in dirs:
            if not StaticDirectory.gql('where path = :1', d).get():
                raise IOError(errno.ENOENT, os.strerror(errno.ENOENT) + (" '%s'" % d))
        self.mtime = time.time()
        return self.put()

    @property
    def is_dir(self):
        return True

ROOT = StaticDirectory.gql('where path = "/"').get()
if not ROOT:
    ROOT = StaticDirectory(path='/').create()

