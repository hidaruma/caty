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
    def get(self, name, default=None):
        return self._dict.get(name, default)

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
        e._dict = self._dict
        return e

    def __repr__(self):
        return repr(self._dict)

    def exists(self, name):
        return name in self._dict

    __contains__ = exists

    def commit(self):
        pass

    def to_name_tree(self):
        return {
            u'kind': u'ns:env',
            u'id': unicode(str(id(self))),
            u'childNodes': {}
        }

