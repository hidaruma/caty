# -*- coding: utf-8 -*- 
# 
# これは、コマンドセットを定義するtempfile.casmと
# ファシリティ実装クラスであるtempfilefcl.pyを繋ぐブリッジコマンド群。
#
# 極めて機械的なルールでブリッジしているので、
# CatyScriptから直接ファシリティ実装クラスのメソッドを呼ぶ方式（Direct Method Call）に
# 変更可能だと思われる。
# 
# いずれ、これらのブリッジコマンド（アダプターレイヤー）は不要となるだろう。
# 

from caty.command import Command
from caty.jsontools import tagged
from tempfilefcl import TempFile # ファシリティ実装クラス

Facility = TempFile

# 全体の管理用コールバック

class MgmntInitialize(Command):
    def execute(self, config):
        r = Facility._initialize(config)
        if r is None:
            return tagged(u'OK', None)
        else:
            return tagged(u'NG', r)

class MgmntFinalize(Command):
    def execute(self):
        Facility._finalize()
        return None

class MgmntCreate(Command):
    def execute(self, mode_param):
        return Facility._create(mode_param)

# インスタンスの管理用コールバック

class MgmntBegin(Command):
    def setup(self, arg0):
        self.arg0 = arg0

    def execute(self):
        reqtr = self.arg0
        reqtr._begin()
        return reqtr

class MgmntCommit(Command):
    def setup(self, arg0):
        self.arg0 = arg0

    def execute(self):
        reqtr = self.arg0
        reqtr._commit()
        return reqtr

class MgmntCancel(Command):
    def setup(self, arg0):
        self.arg0 = arg0

    def execute(self):
        reqtr = self.arg0
        reqtr._cancel()
        return reqtr

class MgmntSync(Command):
    def setup(self, arg0):
        self.arg0 = arg0

    def execute(self):
        reqtr = self.arg0
        reqtr._sync()
        return reqtr

class MgmntClose(Command):
    def setup(self, arg0):
        self.arg0 = arg0

    def execute(self):
        reqtr = self.arg0
        reqtr._close()
        return reqtr

# ファシリティ固有のコマンド

class OsDirPath(Command):
    def setup(self, arg0):
        self.arg0 = arg0

    def execute(self):
        reqtr = self.arg0
        return reqtr.os_dir_path()

class OsPath(Command):
    def setup(self, arg0, name):
        self.arg0 = arg0
        self._name = name

    def execute(self):
        reqtr = self.arg0
        return reqtr.os_path(self._name)

class List(Command):
    def setup(self, arg0):
        self.arg0 = arg0

    def execute(self):
        reqtr = self.arg0
        return reqtr.list()

class Read(Command):
    def setup(self, arg0, name):
        self.arg0 = arg0
        self._name = name

    def execute(self):
        reqtr = self.arg0
        return reqtr.read(self._name)

# ここからmutators

class Write(Command):
    def setup(self, arg0, name):
        self.arg0 = arg0
        self._name = name

    def execute(self, input):
        reqtr = self.arg0
        reqtr.write(input, self._name)
        return reqtr

class Remove(Command):
    def setup(self, arg0, name):
        self.arg0 = arg0
        self._name = name

    def execute(self):
        reqtr = self.arg0
        reqtr.remove(self._name)
        return reqtr
