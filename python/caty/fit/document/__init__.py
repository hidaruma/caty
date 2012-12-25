#coding: utf-8
import caty
from caty.util import escape_html
from caty.fit.document.base import *
from caty.fit.document.literal import *
from caty.fit.document.section import *
from caty.fit.document.setup import *
from caty.fit.document.triple import *
import caty.core.runtimeobject as ro
from caty.core.exception import InternalException

u"""CatyFIT ドキュメントモジュール。
振る舞い定義ファイルから CatyFIT ドキュメントオブジェクトを作成する機能を提供する。

一つの CatyFIT ドキュメントは複数のセットアップセクションとホーアトリプルからなり、
セットアップセクションはファイルやストレージの準備を行う。
場合によってはスクリプトを記述する事も有り得る。

ホーアトリプルは事前条件、本体、事後条件からなり、そのいずれも
テーブルの形で環境変数、セッション、入力、出力などを記述する。
テーブルの一つの行が一つの実行単位であるが、実際には

    セットアップセクション一つ + 事前条件 + 本体 + 事後条件

という実行形態となる。

CatyFIT で実行されるあらゆる処理はロールバックされ、実際の環境への影響はないものとする。
"""

def make_document(seq):
    u"""Wiki 文法の解析結果のリストから Caty FIT ドキュメントを構築する。
    作成された Caty FIT ドキュメントはマクロ展開などがすべて済んだ状態であり、
    テストランナーによって即座にテストの実効が可能な状態になっている。
    """
    fitdoc = FitDocument()
    for node in seq:
        fitdoc.add(node)
    fitdoc.apply_macro()
    fitdoc.compose_triple()
    fitdoc.compose_setup()
    return fitdoc

class FitDocument(object):
    u"""Caty FIT のテストランナーが処理対象とするツリーのルートノード。
    """
    
    def __init__(self):
        u"""ツリーの初期化。
        内部的には Wiki 文書の各要素に対応したノードとマクロ定義の辞書を持つ。
        """
        self._fit_nodes = []
        self._node_maker = NodeMaker(self)

    def add(self, node):
        u"""Wiki 文書の要素を受け取り、 Caty FIT の要素に変換し、ツリーに加える。
        Wiki の要素と異なり Caty FIT の要素はマクロの定義/参照を行い、
        また一部にセクションの概念などを持つため、 behparser で定義されたクラスは使わず、
        専用のクラスを用いる事にする。
        """
        if node.type != 'heading' and self._fit_nodes and self._fit_nodes[-1].is_section:
            self._fit_nodes[-1].add(node)
        else:
            fit_node = self._node_maker.make(node)
            self._fit_nodes.append(fit_node)
            if len(self._fit_nodes) == 1 and self._fit_nodes[0].type != 'title':
                raise Exception(ro.i18n.get(u'CatyFIT must starts with title element'))

    def _is_title_is_unique(self, result, old, node):
        u"""テストのタイトルは常に一つのみとする。
        """
        assert len([n for n in self._fit_nodes if n.type == 'title']) == 1, (node.type, node.lineno)

    def _is_1st_element_title(self, result, old, node):
        u"""Caty FIT のルート直下要素は FitTitle とする。
        """
        assert isinstance(self._fit_nodes[0], FitTitle), (node.type, node.lineno)

    def apply_macro(self):
        u"""マクロのツリー全体への適用。
        """
        macro = {}
        for n in self._fit_nodes:
            n.append_macro(macro)

        for n in self._fit_nodes:
            n.apply_macro(macro)

    def accept(self, test_runner):
        u"""テストランナーの実行処理。
        Visitor パターンで実装する。
        """
        for n in self._fit_nodes:
            n.accept(test_runner)

    def compose_triple(self):
        u"""preCond, body, postCond を triple にまとめる。
        """
        result = []
        precond = None
        body = None
        postcond = None
        for n in self._fit_nodes:
            if n.type == 'preCond':
                if precond:
                    if body is None:
                        raise InternalException(u'$section section appears continuously', section='preCond')
                    else:
                        result.append(FitTriple(precond, body, postcond, self._node_maker))
                        body = None
                        postcond = None
                precond = n
            elif n.type == 'exec':
                if body:
                    result.append(FitTriple(precond, body, postcond, self._node_maker))
                body = n
            elif n.type == 'postCond':
                if body:
                    result.append(FitTriple(precond, body, n, self._node_maker))
                    precond = None
                    body = None
                else:
                    raise InternalException(u'postCond section before body section')
            else:
                if body:
                    result.append(FitTriple(precond, body, postcond, self._node_maker))
                    precond = None
                    body = None
                    postcond = None
                result.append(n)
        if body:
            result.append(FitTriple(precond, body, postcond, self._node_maker))
        self._fit_nodes = result

    def _no_precond_or_body_or_postcond(self, result, old):
        u"""生で preCond, body, postCond は出てこない。
        """
        preconds = len([n for n in self._fit_nodes if n.type == 'preCond']) 
        bodies = len([n for n in self._fit_nodes if n.type == 'exec']) 
        postconds = len([n for n in self._fit_nodes if n.type == 'postCond']) 
        assert preconds == 0
        assert bodies == 0
        assert postconds == 0

    def compose_setup(self):
        u"""file, storage などをすべて setup 配下に納める
        """
        r = []
        setup = None
        for n in self._fit_nodes:
            if n.type == 'setup':
                if setup:
                    r.append(setup)
                setup = n
            elif n.type in ('file', 'storage', 'schema', 'script', 'teardown'):
                if setup:
                    setup.add(n)
                else:
                    raise InternalException(u'$type not belongs to setup section is occured', type=n.type)
            else:
                if setup:
                    r.append(setup)
                    setup = None
                r.append(n)
        self._fit_nodes = r

    def _no_file_or_storage(self, result, old):
        files = len([n for n in self._fit_nodes if n.type == 'file']) 
        strgs = len([n for n in self._fit_nodes if n.type == 'storage']) 
        assert files == 0
        assert strgs == 0

    @property
    def size(self):
        return sum([n.size for n in self._fit_nodes])

class NodeMaker(object):
    def __init__(self, document):
        self._doc = document

    def make(self, node):
        if isinstance(node, FitNode):
            # 一旦 FitNode に変換された場合、再処理はしない
            return node
        if node.type == 'heading':
            if node.level == 1:
                if self._doc.size != 0:
                    raise FitDocumentError(ro.i18n.get(u'Only one title is allowed: Line $line', line=node.lineno))
                return FitTitle(node, self)
            else:
                # XXX: command, literal は必要性についてちと審議中
                #if node.text.startswith('command:'):
                #    return FitCommand(node, self)
                #elif node.text.startswith('literal:'):
                #    return FitLiteral(node, self)
                if node.text.startswith('!name:'):
                    return FitMacro(node, self)
                elif node.text.startswith('!setup'):
                    return FitSetup(node, self)
                elif node.text.startswith('!preCond'):
                    return FitPreCond(node, self)
                elif node.text.startswith('!exec'):
                    return FitExec(node, self)
                elif node.text.startswith('!postCond'):
                    return FitPostCond(node, self)
                elif node.text.startswith('!file:'):
                    return FitFile(node, self)
                elif node.text.startswith('!strg:'):
                    return FitStorage(node, self)
                elif node.text.startswith('!schema'):
                    return FitSchema(node, self)
                elif node.text.startswith('!script'):
                    return FitScript(node, self)
                elif node.text.startswith('!teardown'):
                    return FitTearDown(node, self)
                elif node.text.startswith('!include:'):
                    return FitInclude(node, self)
                else:
                    return FitSection(node, self)

        elif node.type == 'paragraph':
            return FitParagraph(node, self)
        elif node.type == 'code':
            return FitCode(node, self)
        elif node.type == 'table':
            if self._is_macrodef(node.items[0].items):
                return FitMacroTable(node, self)
            return FitTable(node, self)
        assert False, node

    def make_matrix(self, node, command=None):
        header_row = node[0]
        text_list = [n.text.strip(' !').lower() for n in header_row]
        if 'command' in text_list:
            return FitMatrix(node, self, command)
        return FitTable(node, self)

    def make_table(self, node):
        return FitTable(node, self)

    def _is_macrodef(self, items):
        return (len(items) == 2 and
                items[0].text.lower().strip() == 'name' and
                items[1].text.lower().strip() == 'value')



