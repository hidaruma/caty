#coding: utf-8
u"""バージョン管理ツールファシリティモジュール
"""
from caty.core.facility import *
import types

class BaseClient(Facility):
    u"""バージョン管理ツールのフロントエンドクラス。
    このクラスは抽象クラスであり、実際の処理はサブクラスに記述する。
    利用するバージョン管理ツールの種類に制限は付けないが、
    以下の機能は持っており、サーバを立てずとも利用できるものとする。

    * 分割コミット
    * ステータス一覧の取得

    ワーキングコピーとリポジトリが分かれるタイプのバージョン管理ツールの場合、
    ワーキングコピーを pub に、リポジトリを data に置く事を推奨する。
    両者が分かれない場合は pub を利用することになる。
    """
    def __init__(self, app, pub_file, data_file, access_manager=None, path=None):
        Facility.__init__(self)
        self.__wc_fs = pub_file
        self.__repos_fs = data_file
        self.__path = path
        self._access_manager = VCSTransactionManager() if not access_manager else access_manager
        self._app = app
        if self._access_manager:
            self.add = types.MethodType(self._access_manager.update(self.add), self)
            self.checkin = types.MethodType(self._access_manager.update(self.checkin), self)
            self.remove = types.MethodType(self._access_manager.update(self.remove), self)

    # ファシリティの定義しなければならないメソッド

    def start(self):
        return self.clone()

    def clone(self):
        return self.__class__(self._app, self.wc_fs, self.repos_fs, self._access_manager, self.__path)

    def commit(self):
        if self._access_manager:
            self._access_manager.commit()

    def rollback(self):
        if self._access_manager:
            self._access_manager.rollback()

    def __call__(self, path):
        return self.__class__(self._app, self.wc_fs, self.repos_fs, self._access_manager, path)

    def merge_transaction(self, another):
        self._access_manager.merge(another._access_manager)

    @property
    def wc_path(self):
        return self.wc_fs.open(self.__path).real_path

    @property
    def repos_path(self):
        return self.repos_fs.open(self.__path).real_path

    @property
    def wc_fs(self):
        return self.__wc_fs

    @property
    def repos_fs(self):
        return self.__repos_fs

    def get_real_path(self, f):
        return self.wc_fs.open(f).real_path

    def initialize(self):
        raise NotImplementedError(self._app.i18n.get(u'VCS module is not provided by default'))

    def checkin(self, message, *files):
        raise NotImplementedError(self._app.i18n.get(u'VCS module is not provided by default'))

    def add(self, *files):
        raise NotImplementedError(self._app.i18n.get(u'VCS module is not provided by default'))

    def remove(self, *files):
        raise NotImplementedError(self._app.i18n.get(u'VCS module is not provided by default'))

    def list(self):
        raise NotImplementedError(self._app.i18n.get(u'VCS module is not provided by default'))

    def log(self):
        raise NotImplementedError(self._app.i18n.get(u'VCS module is not provided by default'))

    def status(self, *files):
        raise NotImplementedError(self._app.i18n.get(u'VCS module is not provided by default'))

    def diff(self, rev1=None, rev2=None):
        raise NotImplementedError(self._app.i18n.get(u'VCS module is not provided by default'))

class VCSTransactionManager(TransactionalAccessManager):
    def __init__(self):
        TransactionalAccessManager.__init__(self)
        self._queue = []

    def do_update(self, obj, fun, *args, **kwds):
        self._queue.append((obj, fun, args, kwds))

    def do_read(self, obj, fun, *args, **kwds):
        return fun(obj, *args, **kwds)

    def commit(self):
        for obj, fun, args, kwds in self._queue:
            fun(obj, *args, **kwds)
        self._queue = []

    def rollback(self):
        self._queue = []

    def merge(self, another):
        self._queue = another._queue


