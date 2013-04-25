import caty.jsontools.xjson as xjson
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
            key = dirent.basename.split('.')[0]
            if dirent.path.endswith('.xjson') and not dirent.is_dir:
                r[key] = xjson.loads(dirent.read())
            elif dirent.is_dir and self.rec:
                o = self._read(dirent.path)
                if key in r:
                    o.update(r[key])
                r[key] = o
        return r
