#coding: utf-8
from caty.core.command import (Command,
                               PipelineInterruption,
                               PipelineErrorExit,
                               Filter)
from caty.core.exception import *


class MafsMixin(object):
    u"""mafs を扱うコマンドのための mix-in クラス。
    mafs はアプリケーション事に pub, include, data, behaviors といった空間に分離され、
    あるコマンドが pub と include を場合によって使い分ける場合、利用する空間を
    オプションや引数で指定することになる。

    これは非常に煩雑なので、以下のリソース指定形式により、これらの空間を統一的に扱うこととする。

    canonical_path :: ((place '@')? (app ':'))? path
    place :: ('pub'|'include'|'data'|'behaviors')
    app :: [a-zA-Z]+[a-zA-Z0-9-]*

    例えば root アプリケーションの pub の index.html を他のアプリケーションから参照する場合、
    pub@root:/index.html という形で指定することになる。また自身のアプリケーションを指す場合、
    pub@this:/index.html という指定方法になる。

    place が省略された場合は pub が使われ、 app が省略された場合は this が使われる。
    """

    def open(self, path, mode='rb'):
        p, mafs = self.parse_canonical_path(path)
        return mafs.open(p, mode)

    def opendir(self, path):
        p, mafs = self.parse_canonical_path(path)
        return mafs.opendir(p)

    def parse_canonical_path(self, path):
        u"""パス名をパースして place を削除したパス名と place に対応した mafs ファシリティを返す。
        app の指定が this だった場合、それも結果のパス名からは削除される。
        """
        if '@' in path:
            place, path = path.split('@', 1)
        else:
            place = 'pub'
        if path.startswith('this:'):
            path = path.replace('this:', '')

        if place in ('schemata', 'actions'):
            sysfiles = self.sysfiles
            return path, getattr(sysfiles, place)
        else:
            return path, getattr(self, place)
