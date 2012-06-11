# coding:utf-8
from pbc import PbcObject, Contract
from caty.core.application import *
from caty.util import cout, error_to_ustr, brutal_error_printer

from copy import deepcopy
from operator import truth as _
import locale
import codecs
import operator
import os
import sys
import time
import tempfile


class ApplicationGroup(PbcObject):
    u"""Caty アプリケーションをグループ化するオブジェクト。
    管理上の理由により、 Caty のアプリケーションは以下の四つに分類される。

    * main：ユーザ作成のアプリケーション
    * common：フレームワークの提供する共通アプリケーション
    * extra：第三者の配布するアプリケーションの格納場所
    * examples：アプリケーションのサンプル集。本番環境には不要
    
    ApplicationGroup のインスタンスはこれらのアプリケーショングループに対して一つ作成され、
    自身の配下にあるアプリケーションの初期化を行うものとする。
    """

    __properties__ = ['name', 'apps', 'global_config']

    def __init__(self, group_name, global_config, no_ambient, no_app, app_names, system):
        self._name = unicode(group_name)
        self._global_config = global_config
        self._system = system
        self._exists = self._make_super_root(self.name).start().create(u'reads').opendir('/').exists
        self.i18n = system.i18n
        if not self.exists:
            if self._name in (USER):
                self.i18n.write("Application gourp '$name' not exists, auto-generating", name=self._name)
                d = self._make_super_root('').start()
                d.create(u'uses').opendir('/'+self.name).create()
                d.commit()
                self._exists = True
        if self._name == USER:
            d = self._make_super_root(self.name).start()
            r = d.create(u'uses').opendir('/root')
            if not r.exists:
                self.i18nt.write("Root application not exists, auto-generating")
                r.create()
                d.commit()
        if self._exists:
            self._apps = list(self._load_apps(no_ambient, no_app, app_names))
            PbcObject.__init__(self)

    def _load_apps(self, no_ambient, no_app, app_names):
        if self._name == '':
            a = GlobalApplication(u'global', no_ambient, self, self._system)
            if a.enabled:
                yield a
        elif self.exists:
            app_group_root = self._make_super_root(self.name)
            for d in app_group_root.start().create(u'reads').opendir('/').read():
                if d.is_dir and not d.basename[0] in ('.', '_') and not d.basename in self._system.ignore_names:
                    name = d.path.strip('/')
                    if name not in app_names and no_app and self._system.force_app != name:
                        continue
                    if name in RESERVED:
                        throw_caty_exception(
                        u'ERROR_SYSTEM',
                        u'Application name `$name` is reserved', 
                        name=name)
                    try:
                        a = Application(name, no_ambient, self, self._system)
                        if a.enabled:
                            yield a
                    except Exception, e:
                        self.i18n.write("Failed to load '$name': $error", name=name, error=error_to_ustr(e))
                        raise

    def _make_super_root(self, root):
        return self._global_config.mafs_initializer(DummyApplication(), self._system, ROOT)('.', root, self._global_config.mime_types)

    def exec_rc_script(self):
        for app in self._apps:
            app.exec_rc_script()
            app.exec_rc_once_script()

    @property
    def name(self):
        return self._name

    @property
    def apps(self):
        return self._apps

    @property
    def global_config(self):
        return self._global_config

    @property
    def exists(self):
        return self._exists

    @property
    def storage_conf(self):
        return self._global_config.storage_conf

    @property
    def cout(self):
        return self._system.cout

    
    def __invariant__(self):
        if self.exists:
            assert self._global_config
        else:
            assert self._global_config
            assert len(self._apps) == 0


