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
from tempfilefcl import TempFile # ファシリティ実装クラス

Facility = TempFile

# 全体の管理用コールバック

class Initialize(Command):
    def setup(self, config=None):
        self.config = config

    def execute(self, app_instance):
        return Facility.initialize(app_instance, 
                                  self.config)
class Finalize(Command):
    def execute(self, app_instance):
        return Facility.finalize(app_instance)


class Instance(Command):
    def setup(self, system_param=None):
        self.system_param = system_param

    def execute(self, app_instance):
        return Facility.instance(app_instance, self.system_param)


class Create(Command):
    def setup(self, mode=u'use', user_param=None):
        self.mode = mode
        self.user_param = user_param

    def execute(self):
        master = self.arg0
        return master.create(self.mode, self.user_param)

# トランザクション管理用コールバック

class Start(Command):
    def execute(self):
        master = self.arg0
        return master.start()

class Commit(Command):
    def execute(self):
        master = self.arg0
        master.commit()

class Cancel(Command):
    def execute(self):
        master = self.arg0
        master.cancel()

class Cleanup(Command):
    def execute(self):
        master = self.arg0
        master.cleanup()



# ファシリティ固有のコマンド

class OsDirPath(Command):
    def execute(self):
        req = self.arg0
        return req.os_dir_path()

class OsPath(Command):
    def setup(self, name):
        self._name = name

    def execute(self):
        req = self.arg0
        return req.os_path(self._name)

class List(Command):
    def execute(self):
        req = self.arg0
        return req.list()

class Read(Command):
    def setup(self, name):
        self._name = name

    def execute(self):
        req = self.arg0
        return req.read(self._name)

# ここからmutators

class Write(Command):
    def setup(self, name):
        self._name = name

    def execute(self, input):
        req = self.arg0
        req.write(input, self._name)
        return req

class Remove(Command):
    def setup(self, name):
        self._name = name

    def execute(self):
        req = self.arg0
        req.remove(self._name)
