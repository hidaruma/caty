import pkgutil
import os
class AppSpecLibraryImporter(object):
    def __init__(self, app_path):
        self.app_path = os.path.abspath(app_path)
        self.finder = pkgutil.ImpImporter(os.path.join(app_path, 'lib'))
        self.child_path = set()
    
    def add_child(self, app):
        self.child_path.add(app.importer.app_path)

    def find_module(self, fullname, path=None):
        import sys
        mod = self.finder.find_module(fullname, path)
        if mod:
            frame = sys._getframe(1)
            srcpath = os.path.abspath(frame.f_globals['__file__'])
            if not srcpath.startswith(self.app_path):
                for c in self.child_path:
                    if srcpath.startswith(c):
                        break
                else:
                    raise ImportError(fullname)
        return mod
