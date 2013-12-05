from caty.jsontools import xjson
class ManifestReader(object):
    def __init__(self, mafs, name, manifest_dir=u'/prj-manifest', default=None):
        self.mafs = mafs
        self.base_mafenist = name
        self.manifest_dir = manifest_dir
        self.default = default or {}

    def read(self):
        m = self.default
        dm = {}
        with self.mafs.open(self.base_mafenist) as f:
            if f.exists:
                m = xjson.loads(f.read())
                if not isinstance(m, dict):
                    return m
        dir = self.mafs.opendir(self.manifest_dir)
        if not dir.exists:
            return m
        else:
            dm = self._read_dir(dir)
        if m:
            dm.update(m)
        return dm

    def _read_dir(self, dir):
        res = {}
        for e in dir.read():
            if not e.is_dir and e.path.endswith('.xjson'):
                res[unicode(e.basename.rsplit('.', 1)[0])] = ManifestReader(self.mafs, e.path, e.path.rsplit('.', 1)[0]).read()
            elif e.is_dir and not self.mafs.open(e.path + '.xjson').exists:
                res[unicode(e.basename)] = self._read_dir(self.mafs.opendir(e.path))
        return res

class DirectoryWalker(object):
    def __init__(self, mafs, rec, special_file):
        self.mafs = mafs
        self.rec = rec
        self.special_file = special_file

    def read(self, path):
        r = self._read(path)
        if self.special_file:
            o = xjson.loads(self.mafs.open(self.special_file).read())
            r.update(o)
        return r

    def _read(self, path):
        r = {}
        for dirent in self.mafs.opendir(path).read():
            key = unicode(dirent.basename.split('.')[0])
            if dirent.path.endswith('.xjson') and not dirent.is_dir:
                r[key] = xjson.loads(dirent.read())
            elif dirent.is_dir and self.rec:
                o = self._read(dirent.path)
                if key in r:
                    o.update(r[key])
                r[key] = o
        return r

import os
from caty.mafs.fileobject import FileObject, DirectoryObject
from caty.mafs import stdfs
from caty.util.path import join
class FileOpener(object):
    def __init__(self, cwd):
        self.cwd = cwd.replace('\\', '/')

    def opendir(self, path):
        if path.startswith(self.cwd):
            path = path[len(self.cwd):]
        return DirectoryObject(join(self.cwd, path).replace('\\', '/'), stdfs)

    def open(self, path):
        if path.startswith(self.cwd):
            path = path[len(self.cwd):]
        return FileObject(join(self.cwd, path).replace('\\', '/'), 'rb', stdfs)

            
