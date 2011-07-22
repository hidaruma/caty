# coding: utf-8
u"""mafs バックエンドの初期化モジュール。
mafs では標準関数の実装とパス名や権限チェックは切り離され、
自由に組み合わせて使うことが可能である。
このモジュールではそれらのチェック関数と mafs 実装モジュールを組み合わせ、
新たなモジュールを作成する関数を提供する。
"""
import types
from caty.mafs.pathname import default_path_checker
from caty.mafs.pathname import path_checker_combinator as pcc
from caty.mafs.pathname import chroot
from caty.mafs.pathname import trimroot
from caty.mafs import fileobject
from caty.mafs import stdfs
from caty.mafs.metadata import MetadataRegistrar
from caty.core.facility import Facility
from caty.core.resource import Resource
from caty.util.path import join

__all__ = ['build_mafs_module', 'build_fo_module']

def build_mafs_module(fs=stdfs, 
                      root_dir='', 
                      path_checker=default_path_checker, 
                      mime_types=None,
                      encoding='utf-8'):
    u"""mafs モジュール初期化関数。
    fs は mafs 標準関数を定義したモジュールその物である。
    権限チェック関数及びパス名のチェック関数を受け取り、
    それらを fs で定義された標準関数と結合させ、
    結合後の関数を公開メンバとして持つオブジェクトを返す。
    また root_dir を指定することで、 mafs がアクセスできるディレクトリツリーのルートを指定できる。
    デフォルトでは stdfs に simple_checker と default_path_checker を適用し、
    ルートディレクトリの指定を行わないモジュールを返す。
    
    mime_types は str: {'content_type':str, 'is_text': bool} の形式で拡張子に対して
    コンテントタイプとテキストとして扱うかどうかの指定を記述した辞書であり、
    これを元にファイルのメタデータの一部が決定される。
    デフォルトでは全く何も指定されず、 mafs 組み込みのコンテントタイプが適用される。

    encoding は mafs 内部でのデフォルトのエンコーディングタイプを指定する。
    何も指定がなかった場合、 utf-8 が適用される。
    """
    metadata = MetadataRegistrar(mime_types)
    functions = {
        'putFile': pcc(path_checker, root_dir, (fs.putFile)),
        'createFile': pcc(path_checker, root_dir, (fs.createFile)),
        'createDirectory': pcc(path_checker, root_dir, (fs.createDirectory)),
        'readFile': pcc(path_checker, root_dir, (fs.readFile)),
        'readDirectory': pcc(path_checker, root_dir, (fs.readDirectory)),
        'delete': pcc(path_checker, root_dir, (fs.delete)),
        'deleteFile': pcc(path_checker, root_dir, (fs.deleteFile)),
        'deleteDirectory': pcc(path_checker, root_dir, (fs.deleteDirectory)),
        'writeFile': pcc(path_checker, root_dir, (fs.writeFile)),
        'isDir': pcc(path_checker, root_dir, (fs.isDir)),
        #getMetadata は MetadataRegistrar が必要なのでクロージャ使って束縛
        'getMetadata': pcc(path_checker, root_dir, lambda p: (fs.getMetadata(p, metadata))),
        'realPath': pcc(path_checker, root_dir, (fs.realPath)),
        'rename': pcc(path_checker, root_dir, (lambda s, d: fs.rename(s, join(root_dir, d)))),
    }
    module = types.ModuleType('mafsimplement')
    module.__dict__.update(functions)
    module.__dict__['encoding'] = encoding
    module.__dict__['metadata'] = metadata
    module.__dict__['access_manager_factory'] = fs.access_manager_factory
    module.__dict__['__root__'] = root_dir
    return module

class FileObject(fileobject.FileObject, Facility, Resource):
    def __init__(self, path, mode, module):
        fileobject.FileObject.__init__(self, path, mode, module)
        Resource.__init__(self)

    def __invariant__(self):
        assert self.path.startswith('/'), self.path
        fileobject.FileObject.__invariant__(self)

    @property
    def exists(self):
        return self._exists()

    def _exists(self):
        return fileobject.FileObject.exists.fget(self)

    @property
    def last_modified(self):
        return self._last_modified()

    def _last_modified(self):
        return fileobject.FileObject.last_modified.fget(self)

    def _get_name(self):
        return self.path

    def _get_canonical_name(self):
        return '%s:%s' % (self.application.name, self.name)

    #def __del__(self):
    #    self.opener = None
    #    fileobject.FileObject.__del__(self)

class DirectoryObject(fileobject.DirectoryObject, Facility, Resource):
    def __init__(self, path, module):
        if len(path) == path.count('/'):
            fileobject.DirectoryObject.__init__(self, '/', module)
        else:
            fileobject.DirectoryObject.__init__(self, path.rstrip('/'), module)
        Resource.__init__(self)

    def __invariant__(self):
        assert self.path.startswith('/'), self.path

    @property
    def exists(self):
        return self._exists()

    def _exists(self):
        return fileobject.DirectoryObject.exists.fget(self)

    def _get_name(self):
        return self.path

    def _get_canonical_name(self):
        return '%s:%s' % (self.application.name, self.name)

    def _open(self, path, mode='rb'):
        fo = FileObject(path, mode, self.module)
        if self.opener:
            return self.opener._apply_access_manager_to_file(fo)
        else:
            return fo

    def _opendir(self, path):
        fo = DirectoryObject(path, self.module)
        if self.opener:
            return self.opener._apply_access_manager_to_dir(fo)
        else:
            return fo

    #def __del__(self):
    #    self.opener = None

def build_fo_module(module):
    u"""引数の module をバックエンドとして用いるクラスと関数を新たに構築し、
    それらをメンバーとするモジュールを返す。
    引数の module は通常の mafs バックエンドに encoding 属性によってデフォルトエンコーディングが
    指定されたモジュールだとする。
    """

    objects = {
        'FileObject': FileObject,
        'DirectoryObject': DirectoryObject,
        'open': FileObject,
        'opendir': DirectoryObject,
        'get_type': module.metadata.mime_type,
        'is_text_ext': module.metadata.is_text_ext,
        'is_dir': module.isDir,
        'all_types': module.metadata.all_types,
        'access_manager_factory': module.access_manager_factory,
        'encoding': module.encoding,
        'metadata': module.metadata,
    }

    fom = types.ModuleType(str(module.__root__))
    fom.__dict__.update(objects)
    fom.__dict__.update(module.__dict__)
    return fom

