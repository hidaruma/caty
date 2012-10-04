# coding: utf-8
import os
from caty.mafs.authorization import simple_checker, CREATE, READ, UPDATE, DELETE
from caty.core.exception import *
from caty.util import timestamp_from_utime
import tempfile

def createFile(path):
    if path.endswith('/'):
        raise InternalException(u'$path is not file (is directory)', path=path)
    open(path, 'wb')

def putFile(path, contents):
    if path.endswith('/'):
        raise InternalException(u'$path is not file (is directory)', path=path)
    temp = tempfile.mktemp()
    swap = tempfile.mktemp()
    try:
        f = open(temp, 'wb')
        f.write(contents)
        f.close()
        if os.path.exists(path):
            os.rename(path, swap)
        os.rename(temp, path)
        if os.path.exists(swap):
            os.remove(swap)
    except:
        if os.path.exists(path) and not os.path.exists(swap):
            os.remove(path)
        raise
    finally:
        if os.path.exists(temp):
            os.remove(temp)

def createDirectory(path):
    os.mkdir(path)

def deleteFile(path):
    if path.endswith('/'):
        raise InternalException(u'$path is not file (is directory)', path=path)
    os.remove(path)

def deleteDirectory(path):
    os.rmdir(path)

def delete(path):
    if os.path.isdir(path):
        deleteDirectory(path)
    else:
        deleteFile(path)

def readFile(path, text=False):
    if text:
        return open(path, 'rU').read()
    else:
        return open(path, 'rb').read()

def isDir(path):
    return os.path.isdir(path)

def rename(src, dest):
    os.rename(src, dest)

from caty.mafs.metadata import MetadataRegistrar
def getMetadata(path, metadata_registrar=MetadataRegistrar({})):
    mime_type = metadata_registrar.mime_type
    FileMetadata = metadata_registrar.FileMetadata
    DirectoryMetadata = metadata_registrar.DirectoryMetadata
    def getFileMetadata():
        tests =[ lambda s: s.endswith('.icaty'),
                 lambda s: s.endswith('.ictpl'),
                 lambda s: s.startswith('.'),
               ]

        basename = os.path.basename(path)
        for test in tests:
            if test(basename):
                hidden = True
                break
        else:
            hidden = False
        ext = os.path.splitext(path)[-1]
        if not ext:
            ext = os.path.basename(path)
        contentType= mime_type(ext)
        st = os.stat(path)
        contentLength = st.st_size
        lastModified = st.st_mtime
        executable = path.endswith('.caty') or path.endswith('.icaty')
        meta = FileMetadata(contentLength, lastModified, contentType, executable, hidden)
        return meta

    def getDirectoryMetadata():
        st = os.stat(path)
        lastModified = st.st_mtime
        hidden = os.path.basename(os.path.abspath(path)).startswith('.')
        meta = DirectoryMetadata(lastModified, hidden)
        return meta

    if os.path.isdir(path):
        return getDirectoryMetadata()
    else:
        return getFileMetadata()

from caty.mafs.metadata import DirectoryEntry
def readDirectory(path):
    u"""ディレクトリエントリを読み込む。
    """
    for e in os.listdir(path):
        yield DirectoryEntry(e, getMetadata(os.path.join(path, e)))

def writeFile(path, content):
    if path.endswith('/'):
        raise InternalException(u'$path is not file (is directory)', path=path)
    if not os.path.exists(path):
        raise InternalException(u'File does not exists: $path', path=path)
    open(path, 'wb').write(content)

def realPath(path):
    return os.path.abspath(path)

from caty.core.facility import TransactionalAccessManager
from caty.util.collection import MultiMap
import time
class FileTransactionAccessManager(TransactionalAccessManager):
    def __init__(self, module):
        TransactionalAccessManager.__init__(self)
        self._transaction_queue = []
        self._write_queue = MultiMap()
        self._delete_queue = MultiMap()
        self._write_delete_queue = MultiMap()
        self._module = module
        self._mafs_facility = None
        self._observing = set()
    
    def add(self, fo):
        self._observing.add(fo)

    def _apply_facility(self, mafs_facility):
        import weakref
        self._mafs_facility = mafs_facility

    def do_read(self, fo, fun, *args, **kwds):
        self._parent_exists(fo)
        self._not_removed(fo)
        if not fo.is_dir:
            if fo.canonical_name not in self._write_queue:
                if fo.canonical_name not in self._delete_queue:
                    return fun(fo, *args, **kwds)
                else:
                    raise IOError(fo.canonical_name)
            else:
                # flush が起こった後に書き込みされると、 flush 結果を truncate することになる。
                # そのため、 flush 操作後に書き込みがあったらその都度それまでの書き込みをリセットしてるかのように振る舞う
                t = []
                flushed = True
                for x in self._write_queue[fo.canonical_name]:
                    if x[1] is None:
                        flushed = True
                    else:
                        if flushed:
                            flushed = False
                            t = []
                        t.append(x[1])
                return ''.join(t)
        else:
            r = []
            for d in fun(fo, *args, **kwds):
                if d.canonical_name in self._delete_queue:
                    pass
                else:
                    r.append(d)
            for q in self._write_queue.keys():
                if q.startswith(fo.canonical_name):
                    r.append(self.__entry(DirectoryEntry(q.split(':', 1)[1], self._emulate_metadata(q))))
            return r
        assert False, (fo.canonical_name, fun)

    def __entry(self, e):
        #XXX: 再帰的なディレクトリ読み取りに対応してない
        if e.is_dir:
            return self._mafs_facility.DirectoryObject(e.path)
        else:
            return self._mafs_facility.FileObject(e.path, 'rb')


    def do_update(self, fo, fun, *args, **kwds):
        self._parent_exists(fo)
        if fun.__name__ == 'delete':
            self._delete_queue[fo.canonical_name] = None
            self._write_delete_queue[fo.canonical_name] = 'delete'
        elif fun.__name__ == 'create':
            self._write_queue[fo.canonical_name] = (fun.__name__, None, fo)
            self._write_delete_queue[fo.canonical_name] = 'write'
        elif fun.__name__ == 'write':
            self._write_queue[fo.canonical_name] = (fun.__name__, args[0], fo)
            self._write_delete_queue[fo.canonical_name] = 'write'
        elif fun.__name__ == 'flush':
            self._write_queue[fo.canonical_name] = (fun.__name__, None, fo)
        elif fun.__name__ == 'rename':
            self._write_delete_queue[fo.canonical_name] = 'delete'
        elif fun.__name__ == 'flush':
            self._write_queue[fo.canonical_name] = (fun.__name__, None, fo)
        self._transaction_queue.append((fun, fo, args, kwds))

    def do_observed(self, fo, fun, *args, **kwds):
        if fun.__name__ == '_last_modified':
            self._parent_exists(fo)
            if fo.canonical_name in self._write_queue:
                return timestamp_from_utime(time.time())
            else:
                return fun(fo)
        elif fun.__name__ == '_exists':
            if fo.canonical_name in self._write_delete_queue:
                if self._write_delete_queue[fo.canonical_name][-1] == 'delete':
                    return False
                else:
                    return True
            else:
                return fun(fo)
        elif fun.__name__ == 'getMetadata':
            self._parent_exists(fo)
            if fo.canonical_name in self._write_delete_queue:
                if self._write_delete_queue[fo.canonical_name][-1] == 'delete':
                    raise FileIOError(path=fo.path)
                else:
                    return self._emulate_metadata(fo.canonical_name)
            else:
                return fun(fo)
        else:
            raise InternalException(u'Unexpected method call: $method', method=fun.__name__)

    def _parent_exists(self, fo):
        parent_path = fo.canonical_name.rstrip('/').rsplit('/', 1)[0]
        if parent_path.count('/') == 0: return
        assert parent_path != fo.canonical_name, (fo,fo.canonical_name, parent_path)
        if not fo.opener.opendir(parent_path).exists and self._write_delete_queue.get(parent_path+'/', [None])[-1] != 'write':
            raise FileNotFound(path=parent_path)

    def _not_removed(self, fo):
        return fo.canonical_name not in self._delete_queue

    def _emulate_metadata(self, cname):
        metadata_registrar = self._module.metadata
        path = self._write_queue[cname][-1][-1].path
        mime_type = metadata_registrar.mime_type
        FileMetadata = metadata_registrar.FileMetadata
        DirectoryMetadata = metadata_registrar.DirectoryMetadata
        def getFileMetadata():
            tests =[ lambda s: s.endswith('.icaty'),
                     lambda s: s.endswith('.ictpl'),
                     lambda s: s.startswith('.'),
                   ]

            basename = os.path.basename(path)
            for test in tests:
                if test(basename):
                    hidden = True
                    break
            else:
                hidden = False
            ext = os.path.splitext(path)[-1]
            contentType= mime_type(ext)
            contentLength = len(self._write_queue[cname][1])
            lastModified = time.time()
            executable = path.endswith('.caty') or path.endswith('.icaty')
            meta = FileMetadata(contentLength, lastModified, contentType, executable, hidden)
            return meta

        def getDirectoryMetadata():
            lastModified = time.time()
            hidden = os.path.basename(os.path.abspath(path)).startswith('.')
            meta = DirectoryMetadata(lastModified, hidden)
            return meta

        if path.endswith('/'):
            return getDirectoryMetadata()
        else:
            return getFileMetadata()

    def commit(self):
        self._do_transaction()
        self._clear_queue()
        for f in list(self._observing):
            if not f.is_dir and not f.closed:
                f.close()
            f.opener = None

        self._do_transaction()
        self._clear_queue()
        self._detach()

    def cancel(self):
        self._transaction_queue[:] = []
        self._write_queue.clear()
        self._delete_queue.clear()
        self._write_delete_queue.clear()
        self._detach()

    def merge(self, another):
        for q in another._transaction_queue:
            if q not in self._transaction_queue:
                self._transaction_queue.append(q)
        self._write_queue.update(another._write_queue)
        self._delete_queue.update(another._delete_queue)
        self._write_delete_queue.update(another._write_delete_queue)
        for o in another._observing:
            self._observing.add(o)

    def _do_transaction(self):
        for fun, fo, args, kwds in self._transaction_queue:
            fun(fo, *args, **kwds)

    def _clear_queue(self):
        self._transaction_queue[:] = []
        self._write_queue.clear()
        self._delete_queue.clear()
        self._write_delete_queue.clear()

    def _detach_method(self):    
        for fo in self._observing:
            if fo.is_dir:
                fo.read = None
                fo._exists = None
                fo.create = None
                fo.delete = None
                fo.rename = None
                fo.getMetadata = None
            else:
                fo.create = None
                fo.flush = None
                fo.read = None
                fo.write = None
                fo.rename = None
                fo._exists = None
                fo._last_modified = None
                fo.delete = None
                fo.getMetadata = None

    def _detach(self):
        try:
            self._detach_method()
        finally:
            self._observing.clear()
            self.reader.clear()
            self.updator.clear()
            self.observed.clear()
    def clear(self):
        self._module = None
        if '_mafs_facility' in self.__dict__:
            del self._mafs_facility

def access_manager_factory(module):
    return FileTransactionAccessManager(module)




