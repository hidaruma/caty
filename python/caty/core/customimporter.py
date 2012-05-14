import pkgutil
import os
class AppSpecLibraryLoader(object):
    def __init__(self, app_path):
        self.app_path = os.path.abspath(app_path)
        self.finder = pkgutil.ImpImporter(os.path.join(app_path, 'lib'))
    
    def find_module(self, fullname, path=None):
        import sys
        mod = self.finder.find_module(fullname, path)
        if mod:
            frame = sys._getframe(1)
            srcpath = frame.f_globals['__file__']
            if not os.path.abspath(srcpath).startswith(self.app_path):
                raise ImportError(fullname)
        return mod
