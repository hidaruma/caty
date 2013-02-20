#coding:utf-8
from copy import deepcopy
from caty.jsontools import is_json
from caty.jsontools.path import build_query
from time import time

class Undef(object):
    pass
UNDEF = Undef()

class SessionInfo(object):
    u"""セッション情報。
    """

    def __init__(self, key, storage, default=None, created=None):
        self.__key = key
        self.__session_obj = {} if default is None else default
        self.__storage = storage
        self.__created = time() if created is None else created

    @property
    def storage(self):
        return self.__storage

    @property
    def key(self):
        return self.__key

    @property
    def created(self):
        return self.__created

    def values(self):
        return self.__session_obj.values()

    def keys(self):
        return self.__session_obj.keys()

    def items(self):
        return self.__session_obj.items()

    def exists(self, name):
        u"""name に対応した値が格納されている場合 True を返す。
        """
        return name in self.__session_obj
    
    __in__ = exists

    def get(self, name, default=UNDEF):
        u"""name に対応した値を返す。
        """
        if default == UNDEF:
            return self.__session_obj[name]
        else:
            if name in self.__session_obj:
                return self.__session_obj[name]
            else:
                return default

    def __getitem__(self, name):
        return self.__session_obj[name]

    def find(self, name, sjpath):
        u"""SJPath を用いて値を返す。
        """
        return build_query(sjpath).find(self.get(name))

    def put(self, name, value):
        u"""値の格納。値が存在する場合は例外を送出する。
        格納できる値は Caty において拡張 JSON の値として認められるものに限る。
        すなわち、int, decimal, bool, dict, list, None, unicode, str 及びタグの組み合わせである。
        """
        assert is_json(value), u'JSON でない値は格納できません'
        self.__session_obj[name] = value
        return

    __setitem__ = put

    def clear(self, clear_reserved_handles=False):
        u"""セッション変数をすべて削除する。
        """
        self.__session_obj.clear()

    def _to_dict(self):
        objects = deepcopy(self.__session_obj)
        return {
            'key': self.__key,
            'objects': objects,
        }

    def update_time(self):
        self.__created = time() 

    def commit(self):
        if self.__storage is not None:
            self.__storage.store(self)

from caty.core.facility import Facility, AccessManager
class SessionInfoWrapper(Facility):
    u"""セッション情報へのラッパー。
    Caty コマンドはコマンド宣言によりセッションに対して読み書きモードを宣言できる。
    その宣言によってコマンドが可能な操作を制限する必要があり、そのためのラッパークラスを用意する。
    """
    def __init__(self, session):
        self.__session = session
        Facility.__init__(self)

    @property
    def storage(self):
        return self.__session.storage

    @property
    def id(self):
        return self.__session.key

    @property
    def created(self):
        return self.__session.created

    am = AccessManager()

    def exists(self, name):
        u"""name に対応した値が格納されている場合 True を返す。
        """
        return self.__session.exists(name)

    __contains__ = exists

    @am.read
    def get(self, name, default=None):
        u"""name に対応した値を返す。
        """
        return self.__session.get(name, default)

    @am.read
    def __getitem__(self, name):
        return self.__session[name]

    @am.read
    def find(self, name, sjpath):
        u"""SJPath を用いて値を返す。
        """
        return self.__session.find(name, sjpath)

    @am.update
    def put(self, name, value):
        u"""値の格納。値が存在する場合は例外を送出する。
        """
        self.__session.put(name, value)

    __setitem__ = put

    @am.update
    def clear(self):
        u"""セッション変数をすべて削除する。
        """
        self.__session.clear()

    def _to_dict(self):
        return self.__session._to_dict()

    def __repr__(self):
        return repr(self._to_dict())

    def items(self):
        return self.__session.items()

    def merge_transaction(self, another):
        x = dict(self.__session.items())
        y = dict(another.items())
        x.update(y)
        self.__sesssion = SessionInfo(self.__session.key, self.__session.storage, x, self.__session.created)

    def commit(self):
        self.__session.commit()

    def clone(self):
        return SessionInfoWrapper(self.__session)

    def update_time(self):
        self.__session.update_time()

    def to_name_tree(self):
        return {
            u'kind': u'ns:session',
            u'id': unicode(str(id(self))),
            u'childNodes': {}
        }

def create_variable():
    e = SessionInfo('env', None)
    return SessionInfoWrapper(e)

