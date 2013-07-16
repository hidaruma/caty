# coding: utf-8
from __future__ import with_statement
import os
from datetime import datetime
from caty.mafs import stdfs
from caty.mafs.metadata import timestamp_from_utime
from caty.util import path

class FileObject(object):
    u"""mafs のファイルオブジェクト。
    このクラス自体はファイルシステムへのアクセス機能を持たず、
    個々の mafs 実装で定義された関数へのラッパーオブジェクトとして機能する。
    """
    def __init__(self, path, mode, module):
        self.__path = path
        self.__module = module
        self.__buffer = []
        self.__mode = mode
        self.__closed = False
        self.__read = False
        self.__buffer = []
        self.__deleted = False

    def list_parents(self):
        return list(path.list_hierarchy(self.__path))[:-1]

    @property
    def path(self):
        return self.__path

    @property
    def basename(self):
        return self.path.rsplit('/', 1)[-1]

    @property
    def content_length(self):
        return self.getMetadata().contentLength

    @property
    def last_modified(self):
        return self.getMetadata().lastModified

    @property
    def content_type(self):
        return unicode(self.getMetadata().contentType)

    @property
    def is_text(self):
        return self.getMetadata().isText

    @property
    def encoding(self):
        return unicode(self.__module.encoding)

    @property
    def is_executable(self):
        return self.getMetadata().executable

    @property
    def is_hidden(self):
        return self.getMedata().hidden

    def getMetadata(self):
        return self.__module.getMetadata(self.path)

    @property
    def exists(self):
        try:
            self.last_modified
            return True
        except Exception as e:
            return False

    def mode():
        def _get(self):
            return self.__mode
        def _set(self, value):
            if not value in  ('rb', 'wb'):
                raise Exception('Invalid mode: %s' % value)
            self.__mode = value
        return _get, _set
    mode = property(*mode())

    @property
    def closed(self):
        return self.__closed

    def closed_check(f):
        def _(self, *args, **kwds):
            if self.closed:
                raise Exception('Already closed: %s' % self.path)
            else:
                return f(self, *args, **kwds)
        _.__name__ = f.__name__
        _.__doc__ = f.__doc__
        return _

    def read(self):
        u"""ファイルの内容をすべて読み出す。
        読み取り権限を持たない場合、例外を送出する。
        """
        if self.__read: return ''
        self.__read = True
        if self.is_text:
            data = self.__module.readFile(self.path, True)
            return unicode(data, self.__module.encoding)
        else:
            data = self.__module.readFile(self.path)
            return data

    def create(self):
        u"""空のファイルを作成する。
        """
        self.__module.createFile(self.path)

    def write(self, content):
        u"""ファイルへの書き込みを行う。
        ファイルが存在しない場合はエラーとなる。
        """
        assert self.mode == 'wb'
        if isinstance(content, unicode):
            data = content.encode(self.__module.encoding)
        else:
            data = content
        self.__buffer.append(data)
    
    def close(self):
        u"""ファイルを閉じる。
        一旦閉じられたファイルオブジェクトは再利用できない。
        """
        if self.closed: return
        if self.__deleted: return
        if self.mode == 'wb':
            if not self.exists:
                self.create()
            self.flush()
        self.__closed = True

    def flush(self):
        if self.__buffer:
            data = ''.join(self.__buffer)
            self.__module.putFile(self.path, data)
            self.__buffer = []

    def delete(self, dummy=False):
        r"""ファイルを削除する。
        dummy 引数は DirectoryObject とのインターフェースを合致させるためのものである。
        """
        self.__closed = True
        self.__deleted = True
        self.__module.deleteFile(self.path)

    def is_modifed_since(self, ts):
        u"""引数の時刻とファイルのタイムスタンプを比べ、
        ファイルの方が新しければ True を返す。
        引数の型は float もしくは datetime オブジェクトのみを受け付ける。
        """
        if isinstance(ts, float):
            ts = timestamp_from_utime(ts)
        elif not isinstance(ts, datetime):
            raise TypeError('Type of argument must be float or datetime')
        return self.last_modified > ts

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.closed:
            self.close()
        if not exc_type and not exc_value and not traceback:
            return True
        else:
            return False

    def rename(self, path):
        self.__module.rename(self.path, path)

    @property
    def is_dir(self):
        return False

    @property
    def real_path(self):
        return self.__module.realPath(self.path)

class DirectoryObject(object):
    u"""mafs におけるディレクトリ。
    """
    def __init__(self, path, module):
        self.__path = path if path.endswith('/') else path + '/'
        self.__module = module

    @property
    def path(self):
        return self.__path

    @property
    def last_modified(self):
        return self.getMetadata().lastModified

    @property
    def is_hidden(self):
        return self.getMetadata().hidden

    def getMetadata(self):
        return self.__module.getMetadata(self.path)

    @property
    def exists(self):
        try:
            self.last_modified
            return True
        except Exception, e:
            return False

    def list_parents(self):
        return list(path.list_hierarchy(self.__path.rstrip(u'/')))[:-1]

    def create(self):
        r"""ディレクトリを作成する。
        """
        self.__module.createDirectory(self.path)

    def read(self, recursive=False):
        u"""path 直下のディレクトリエントリを FileObject または DirectoryObject のジェネレータとして返す。
        recursive = True の時、再帰的にディレクトリをたどる。
        """
        for e in self.__module.readDirectory(self.path):
            if e.is_dir:
                if not recursive:
                    yield self._opendir(path.join(self.path, e.name))
                else:
                    for se in self._opendir(path.join(self.path, e.name)).read(recursive):
                        yield se
            else:
                yield self._open(path.join(self.path, e.name), 'rb')

    def delete(self, recursive=False):
        u"""ディレクトリを削除する。
        recursive が True の場合、再帰的にディレクトリを削除する。
        """
        if recursive:
            for e in self._internal_read(recursive):
                e.delete(recursive)
            self.__module.deleteDirectory(self.path)
        else:
            self.__module.deleteDirectory(self.path)

    @property
    def is_dir(self):
        return True

    def close(self):
        pass

    @property
    def real_path(self):
        return self.__module.realPath(self.path)

    @property
    def basename(self):
        return os.path.basename(self.path.rstrip('/')) or '/'

    def _open(self, path, mode='rb'):
        return FileObject(path, mode, self.__module)

    def _opendir(self, path):
        return DirectoryObject(path, self.__module)

    def _internal_read(self, recursive=False):
        u"""通常の read と同様だが、 mafs のトランザクション制御を受けない形での read となる。
        これは delete メソッドの再帰処理に際して起こる問題への対処である。
        通常の read で返されるオブジェクトは mafs のトランザクション制御下にあり、
        そのオブジェクトを delete しようとすると当然だがトランザクションキューに入れられる。
        ところが親ディレクトリの再帰的 delete が呼ばれている場合、
        先にトランザクションキューに親の delete が登録されてしまうため、
        子ノードの delete が不正な処理となってしまう。
        そのため、トランザクション実行時には mafs のトランザクションを経由せずに
        delete を行わなければならない。
        """
        for e in self.__module.readDirectory(self.path):
            if e.is_dir:
                d = DirectoryObject(path.join(self.path, e.name), self.__module)
                if recursive:
                    for se in d._internal_read(recursive):
                        yield se
                yield d
            else:
                yield FileObject(path.join(self.path, e.name), 'rb', self.__module)

    def rename(self, path):
        self.__module.rename(self.path, path)

    @property
    def module(self):
        return self.__module


