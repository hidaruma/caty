#coding:utf-8
from caty.util import escape_html

class FitNode(object):
    def __init__(self, node, node_maker):
        self._node_maker = node_maker
        self._build(node)

    def accept(self, test_runner):
        u"""必ずサブクラスで実装すること
        """
        raise NotImplementedError()

    def apply_macro(self, macro_dict):
        u"""マクロ適用が必要なのはテーブルとコマンドセクションのみなので、デフォルトは空メソッド。
        """
        pass

    def append_macro(self, macro_dict):
        pass

    @property
    def size(self):
        u"""テーブルとコマンドセクション以外は子要素を持たないので、常に 1 を返せばよい。
        """
        return 1

    def to_html(self):
        raise NotImplementedError()

    is_section = False

class FitDocumentError(Exception):
    pass

