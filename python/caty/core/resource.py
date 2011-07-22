#coding: utf-8
u"""抽象リソースモジュール

== 概略

Caty におけるリソースとは、以下のものである。

* スキーマ
* コマンド
* ファイル
* JSON ストレージのテーブル

これらのリソースはアプリケーション毎に排他になっており、
通常は他のモジュールのリソースを参照することはできない。
ただし、リソースに対する完全修飾名を指定することで参照可能となる。

スキーマ参照の場合：
{{{
type x = <app>pkg.mod:Type;
}}}

コマンド呼び出しの場合：
{{{
"input" | app#pkg.mod:Cmd;
}}}

ファイル参照の場合：
{{{
f = self.pub.open('app:/x.txt')
i = self.include.open('app:/include.html')
}}}

JSON ストレージはリソースであるが、すべてのアプリケーションが同一のデータベースを用いるため、
特にアプリケーションごとに絞り込みをするような事は行っていない。

== リソース名の重複

組み込みのコマンド・スキーマ・テーブルと同名のリソースは追加できない。
また common ディレクトリの下にあるものと同名のファイルの存在も許されない。

== ファシリティとの関係

ファシリティとリソースは関連のある概念であるが、イコールの関係にはない。
例えば以下にあげるものはファシリティではあるがリソースではない。

* Caty インタープリタ
* セッション
* 環境変数
* スレッドローカル

また、以下にあげるものはリソースではあるがファシリティではない。

* スキーマ
* コマンド

== リソースファインダー

リソースへのアクセス手段を提供するオブジェクトとして、リソースファインダーを定義する。
リソースファインダーは標準的には __call__ によってリソースを返す、
外部的にはファクトリ関数のように見えるよう動作する。

リソースファインダーはファシリティである場合がある。

* スキーマを取得するためのリソースファインダー
* ファイルを取得するリソースファインダー

これらはファシリティとしても扱われ、最初のものは read-only ファシリティ、
残りは read/write 可能でトランザクション可能なファシリティである。

一方、コマンド取得のリソースファインダーはファシリティではない。

"""

class Resource(object):
    u"""リソースオブジェクト。
    リソース自体は抽象的な概念なので、このクラスでは個々のリソース自体の性質は一切定義しない。
    このクラスではリソースが共通して持つべき以下の性質を定めるに止める。

    * 所属するアプリケーションへの参照
    * 自身のリソースタイプ
    * 自身を参照するための完全修飾名
    * 完全修飾名でない名前

    これらのうち、所属するアプリケーションへの参照は None 値が許され、
    その場合は組み込みのリソースということになる。
    他は全て何らかの意味ある値を返す必要がある。
    """

    def __init__(self, application=None):
        self.__application = application

    def application():
        def get(self):
            return self.__application

        def set(self, value):
            self.__application = value

        return get, set

    application = property(*application())

    @property
    def resource_type(self):
        return self._get_resource_type()

    @property
    def name(self):
        return self._get_name()

    @property
    def canonical_name(self):
        return self._get_canonical_name()

    def _get_resource_type(self):
        raise NotImplementedError(repr(self))

    def _get_name(self):
        raise NotImplementedError(repr(self))

    def _get_canonical_name(self):
        raise NotImplementedError(repr(self))
        
class ResourceFinder(object):
    u"""リソース検索オブジェクト。
    リソースへのアクセスを提供するオブジェクトは必ずこのクラスを継承する。
    """
    def __init__(self, application, system):
        self.__application = application
        self.__system = system
    
    @property
    def system(self):
        return self.__system

    def __call__(self, key):
        raise NotImplementedError()

    def application():
        def get(self):
            return self.__application

        def set(self, value):
            self.__application = value

        return get, set

    application = property(*application())


