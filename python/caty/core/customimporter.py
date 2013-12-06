#coding:utf-8
import os
import pkgutil
import sys
_importers__cache = {}
class AppSpecLibraryImporter(object):
    def __init__(self, app_path):
        self.app_path = os.path.abspath(app_path)
        self.finder = pkgutil.ImpImporter(os.path.join(app_path, 'lib'))
        frame = sys._getframe(0)
        self.child_path = set()
        self.imported_modules = set()
    
    def add_child(self, app):
        self.child_path.add(app.importer.app_path)

    def find_module(self, fullname, path=None):
        loader = self.finder.find_module(fullname, path)
        if loader:
            try:
                self._check_path(fullname)
            except ImportError:
                return None
            _importers__cache[fullname] = self
            self.imported_modules.add(fullname)
            return loader

    def discard(self):
        for n in self.imported_modules:
            try:
                if n in sys.modules:
                    del sys.modules[n]
                for m in list(sys.modules.keys()):
                    if m.startswith(n+'.'):
                        del sys.modules[m]
                if n in _importers__cache:
                    del _importers__cache[n]
            except Exception as e:
                print (e)
                pass
        self.imported_modules = set()

    def _check_path(self, fullname, level=3):
        frame = sys._getframe(level)
        srcpath = os.path.abspath(frame.f_globals['__file__'])
        if not srcpath.startswith(self.app_path):
            for c in self.child_path:
                if srcpath.startswith(c):
                    break
            else:
                raise ImportError(fullname)

def make_custom_import():
    import __builtin__
    import functools
    origin = __builtin__.__import__
    __builtin__.__import__ = functools.partial(custom_import, importer=origin)
    
def custom_import(name, globals={}, locals={}, fromlist=[], level=-1, importer=None):
    if name in _importers__cache:
        _importers__cache[name]._check_path(name, 2)
    return importer(name, globals, locals, fromlist, level)


