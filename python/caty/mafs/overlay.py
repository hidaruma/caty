#coding: utf-8
from caty.core.facility import ReadOnlyFacility
from caty.core.exception import InternalException
class MafsOverlay(ReadOnlyFacility):
    u"""common 配下のスキーマ、コマンド、スクリプトなどの
    Read Only なリソースを透過的に扱うためのラッパークラス。
    common/schemata/foo.casm と site/$SITE_NAME/schemata/bar.casm を
    それぞれ foo.casm, bar.casm でアクセス可能とし、名前が被っていたら
    即座にエラーする（あるいは最初に見つかったものを返す）などが目的である。
    スキーマ処理は Read Only なため、単純にオーバーレイしてしまってよい。
    """
    def __init__(self, *filesystems, **kwds):
        self._filesystems = filesystems
        self._error_on_dup = kwds.get('error_on_dup', True)

    def open(self, path):
        fs = list((x for x in self._filesystems if x.open(path).exists))
        if len(fs) > 1 and self._error_on_dup:
            raise InternalException(u'Duplicated path name: $path', path=path)
        return fs[0].open(path)

    def DirectoryObject(self, path):
        return OverlayedDirectory(self._filesystems, path)

    def clone(self):
        return self

class OverlayedDirectory(object):
    def __init__(self, filesystems, path):
        self._filesystems = filesystems
        self._path = path

    def read(self, recursive=False):
        for fs in self._filesystems:
            d = fs.DirectoryObject(self._path)
            if not d.exists: continue
            for e in d.read(recursive):
                yield e



