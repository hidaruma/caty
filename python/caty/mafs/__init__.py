#coding:utf-8
from caty.mafs.builder import build_mafs_module, build_fo_module
from caty.core.facility import Facility, READ, UPDATE, DUAL
from caty.core.resource import ResourceFinder
from caty.core.exception import throw_caty_exception
from caty.util import bind1st
import caty

from pbc import PbcObject, Contract

import types
import weakref
def initialize(app, system, type, **kwds):
    root = kwds['root_dir']
    fs = build_fo_module(build_mafs_module(**kwds))
    access_manager_factory = fs.access_manager_factory
    return MafsFactory(fs, root, access_manager_factory, app, system, type)

class MafsFactory(Facility, ResourceFinder, PbcObject):
    def __init__(self, 
                 module,
                 root,
                 access_manager_factory,
                 application,
                 system,
                 type,
                 manager=None,
                 origin=False):
        Facility.__init__(self)
        ResourceFinder.__init__(self, application, system)
        self._root = root
        self._mod = module
        self._access_manager_factory = access_manager_factory
        self._access_manager = manager
        self._type = type
        self.__closed = False
        self.__origin = origin
        PbcObject.__init__(self)
    
    ################################################
    # ファシリティが定義しなければならないメソッド #
    ################################################

    def start(self):
        n = MafsFactory(self._mod, 
                           self._root, 
                           self._access_manager_factory, 
                           self.application,
                           self.system,
                           self._type,
                           self._access_manager_factory(self._mod),
                           True)
        n._access_manager._apply_facility(n)
        return n

    def clone(self):
        return MafsFactory(self._mod, 
                           self._root, 
                           self._access_manager_factory, 
                           self.application,
                           self.system,
                           self._type,
                           self._access_manager)

    def commit(self):
        self._access_manager.commit()
 
    def cleanup(self):
        self._access_manager.clear()

    def rollback(self):
        self._access_manager.rollback()

    def merge_transaction(self, another):
        self._access_manager.merge(another._access_manager)

    def application():
        def get(self):
            return ResourceFinder.application.fget(self)
        def set(self, app):
            new = self._dispatch(app)
            MafsFactory.__init__(self,
                                 new._mod, 
                                 new._root, 
                                 new._access_manager_factory, 
                                 new.application, 
                                 new.system, 
                                 new._type,
                                 new._access_manager)
            Facility.__init__(self, new.mode)
        return get, set
    application = property(*application())

    ##################
    # モジュール関数 #
    ##################

    @property
    def get_type(self):
        return self._mod.get_type

    @property
    def is_text_ext(self):
        return self._mod.is_text_ext

    @property
    def all_types(self):
        return self._mod.all_types

    @property
    def is_dir(self):
        return self._mod.is_dir

    #########################################
    # ファイル/ディレクトリオープンメソッド #
    #########################################

    def open(self, path, mode='rb'):
        path, another = self._parse_canonical_path(path)
        if another:
            return another.open(path, mode)
        else:
            fo = self._mod.open(path, mode, self._mod)
            return self._apply_access_manager_to_file(fo)

    def opendir(self, path):
        path, another = self._parse_canonical_path(path)
        if another:
            return another.opendir(path)
        else:
            fo = self._mod.opendir(path, self._mod)
            return self._apply_access_manager_to_dir(fo)

    def FileObject(self, path, mode):
        path, another = self._parse_canonical_path(path)
        if another:
            return another.FileObject(another_path, mode)
        else:
            fo = self._mod.FileObject(path, mode, self._mod)
            return self._apply_access_manager_to_file(fo)

    def DirectoryObject(self, path):
        path, another = self._parse_canonical_path(path)
        if another:
            return another.DirectoryObject(path)
        else:
            fo = self._mod.DirectoryObject(path, self._mod)
            return self._apply_access_manager_to_dir(fo)

    def _parse_canonical_path(self, path):
        import re
        c = re.compile('([-a-zA-Z0-9_]+):/')
        m = c.match(path)
        if m:
            if self.application.name != m.group(1) and m.group(1) != 'this':
                another = self._another_mafs(path)
                another_path = path.split(':', 1)[1]
                return another_path, another
            else:
                return path.split(':', 1)[1], None
        else:
            return path, None

    def _another_mafs(self, path):
        app_name = path.split(':/')[0]
        if app_name == 'this':
            app = self.application
        elif app_name not in self.system.app_names:
            throw_caty_exception(
                u'APP_NOT_FOUND',
                u'Application does not exists: $name', name=app_name)
        else:
            app = self.system.get_app(app_name)
        return self._dispatch(app)

    def _dispatch(self, app):
        if self._type == 'pub':
            mafs = app.pub
        elif self._type == 'include':
            mafs = app.include
        elif self._type == 'scripts':
            mafs = app.scripts
        elif self._type == 'data':
            mafs = app.data
        elif self._type == 'behaviors':
            mafs = app.behaviors
        elif self._type == 'schemata':
            mafs = app._schema_fs
        mf = MafsFactory(mafs._mod, 
                           self._root, 
                           self._access_manager_factory, 
                           app,
                           self.system,
                           self._type,
                           self._access_manager)
        if self.mode == READ:
            return mf.read_mode
        elif self.mode == UPDATE:
            return mf.update_mode
        else:
            return mf.dual_mode

    def _apply_access_manager_to_file(self, fo):
        Facility.__init__(fo, self.mode)
        fo.create = types.MethodType(self._access_manager.update(fo.create), fo)
        fo.flush = types.MethodType(self._access_manager.update(fo.flush), fo)
        fo.read = types.MethodType(self._access_manager.read(fo.read), fo)
        fo.write = types.MethodType(self._access_manager.update(fo.write), fo)
        fo.rename = types.MethodType(self._access_manager.update(fo.rename), fo)
        fo._exists = types.MethodType(self._access_manager.observe(fo._exists), fo)
        fo._last_modified = types.MethodType(self._access_manager.observe(fo._last_modified), fo)
        fo.delete = types.MethodType(self._access_manager.update(fo.delete), fo)
        fo.getMetadata = types.MethodType(self._access_manager.observe(fo.getMetadata), fo)
        fo.opener = self
        fo.application = self.application
        self._access_manager.add(fo)
        return fo

    def _apply_access_manager_to_dir(self, fo):
        Facility.__init__(fo, self.mode)
        fo.read = types.MethodType(self._access_manager.read(fo.read), fo)
        fo._exists = types.MethodType(self._access_manager.observe(fo._exists), fo)
        fo.delete = types.MethodType(self._access_manager.update(fo.delete), fo)
        fo.create = types.MethodType(self._access_manager.update(fo.create), fo)
        fo.rename = types.MethodType(self._access_manager.update(fo.rename), fo)
        fo.getMetadata = types.MethodType(self._access_manager.observe(fo.getMetadata), fo)
        fo.opener = self
        fo.application = self.application
        self._access_manager.add(fo)
        return fo

    def __invariant__(self):
        assert self._type in ('pub', 
                              'include', 
                              'scripts', 
                              'data', 
                              'behaviors',
                              'commands',
                              'schemata',
                              'messages',
                              'actions',
                              'root'), self._type
        # root はシステム初期化時にのみ使われる特殊な値

    if caty.DEBUG:
        def _access_manager_not_none(self, path):
            assert self._access_manager is not None

        def _same_type(self, result, old, path):
            assert result._type == self._type

        _another_mafs = Contract(_another_mafs)
        _another_mafs.require += _access_manager_not_none
        _another_mafs.ensure += _same_type

