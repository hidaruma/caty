#coding: utf-8
from caty.jsontools import xjson as json

class PluginMap(object):
    def __init__(self):
        self.__fs = None
        self.__plugin_map = {}
        self.__obj_map = {}

    def set_fs(self, fs):
        self.__fs = fs

    def feed(self, s):
        d = json.loads(s)
        for k, v in d.items():
            self.__plugin_map[k] = self._load_plugin(v)

    def _load_plugin(self, o):
        cls, path = self._extract_cls(o['refers'])
        if path not in self.__obj_map:
            self.__obj_map[path] = {}
            udt = o['underlying']
            code = self.__fs.open(path).read()
            enc = self._find_encoding(code)
            obj = compile(code.encode(enc), path, 'exec')
            exec obj in self.__obj_map[path]
        return self.__obj_map[path][cls]
 
    def get_plugin(self, name):
        return self.__plugin_map[name]()

    def _extract_cls(self, r):
        _, rest = r.split(':')
        m, c = rest.rsplit('.', 1)
        p = '/' + m.replace('.', '/') + '.py'
        return c, p


    def _find_encoding(self, text):
        import re
        line = text.splitlines()[0]
        c = re.compile('coding *: *(.+)')
        m = c.search(line)
        if m:
            return m.group(1)
        return 'utf-8'



