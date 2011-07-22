# coding: utf-8
import codecs
import os
import sys
class IResourceIO(object):
    u"""テンプレートにおける IO 処理インターフェース。
    """

    def open(self, path, mode):
        u"""ビルトイン関数の open 同様の機能とする。
        """
        raise NotImplementedError

    def last_modified(self, path):
        u"""os.stat と同様の機能とする。
        """
        raise NotImplementedError

    def exists(self, path):
        u"""os.path.exists と同様の機能とする。
        """
        raise NotImplementedError

class ResourceIO(IResourceIO):
    u"""通常のファイルシステムをベースにした実装。
    テストあるいはテンプレートエンジン単体で動作させるために用いる。
    caty アプリケーションでは mafs をバックエンドにした実装と差し替えること。
    """
    def __init__(self):
        self._encoding = sys.getdefaultencoding()

    def open(self, path, mode='r'):
        return codecs.getreader(self._encoding)(open(path, mode))

    def last_modified(self, path):
        return os.stat(path).st_mtime

    def exists(self, path):
        return os.path.exists(path)


