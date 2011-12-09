#coding: utf-8
from caty.core.facility import Facility, AccessManager
from caty.core.exception import InternalException

class Env(Facility):
    def __init__(self):
        self._dict = {}
        Facility.__init__(self)

    def start(self):
        return self.clone()

    def items(self):
        return self._dict.items()

    am = AccessManager()

    @am.read
    def get(self, name):
        return self._dict[name]

    @am.update
    def put(self, name, value):
        u"""値の格納。値が存在する場合は例外を送出する。
        """
        if self.exists(name): 
            raise InternalException(u'Can not overwrite environment variable')
        self._dict[name] = value
        return

    __setitem__ = put

    __getitem__ = get

    def clone(self):
        e = Env()
        for k, v in self._dict.items():
            e._dict[k] = v
        return e

    def __repr__(self):
        return repr(self._dict)

    def exists(self, name):
        return name in self._dict

    def commit(self):
        pass

    def to_name_tree(self):
        return {
            u'kind': u'ns:env',
            u'id': unicode(str(id(self))),
            u'childNodes': {}
        }

