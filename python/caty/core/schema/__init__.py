#coding: utf-8
u"""Caty スキーマモジュール。
Caty では JSON スキーマを元にした独自のスキーマ言語をアプリケーション全体にわたって利用する。
このモジュールではスキーマの構文については特に定義せず、スキーマの動作について定義する。

== 概観

Caty におけるスキーマモジュールの実体は、以下のサブモジュール群によって実装される。

;caty.core.schema.base
:すべてのスキーマのベースクラス及びユニオン型、タグ付き型、ユーザ定義型などの実装
;caty.core.schema.number
:数値（整数）型の実装
;caty.core.schema.string
:文字列型の実装
;caty.core.schema.binary
:バイナリ型の実装
;caty.core.schema.bool
:真偽値型の実装
;caty.core.schema.object
:オブジェクト型の実装
;caty.core.schema.array
;配列型の実装

以上のモジュール群によって、以下の組み込み型を定義する。

* integer
* number
* string
* binary
* boolean
* object
* array
* any
* null
* void
* never

以上の型及びそれらの型に対するタグ付けは無条件に利用可能である。
上記のリストに無い型は全てユーザ定義型である。
Caty フレームワークの標準ライブラリで定義されている型も同様であり、
「Caty コアで定義されている型」と言った場合、上記の組み込み型のみを指す。

== スキーマの使われる場面

主にスキーマは以下の場面で利用される。

* Caty スクリプト内部での型検証
* 外部入力に対する変換処理

Caty スクリプトの詳細は caty.core.script モジュールを参照すること。
Caty スクリプトは強く型付けされた言語であり、その型システムが Caty スキーマである。
またスキーマは検証だけでなく値の変換機能も有する。
これは主に Web 入力に対して適用され、フォームから入力されたデータを
スキーマを通して変換し、 Caty 内部で利用できるオブジェクトにすると同時に異常な入力の排除を行う。

"""

from caty.core.schema.base import *
from caty.core.schema.number import NumberSchema, IntegerSchema
from caty.core.schema.string import StringSchema
from caty.core.schema.binary import BinarySchema
from caty.core.schema.bool import BoolSchema
from caty.core.schema.array import ArraySchema
from caty.core.schema.object import ObjectSchema, PseudoTag
from caty.core.schema.enum import EnumSchema
from caty.core.schema.bag import BagSchema
from caty.core.schema.exponent import ExponentSchema
__all__ = [
    "SchemaBase",
    "OperatorSchema",
    "UnionSchema",
    "IntersectionSchema",
    "UpdatorSchema",
    "TagSchema",
    "ScalarSchema",
    "AnySchema",
    "NullSchema",
    "VoidSchema",
    "NeverSchema",
    "UndefinedSchema",
    "TypeVariable",
    "OptionalSchema",
    "UnivSchema",
    "ForeignSchema",
    "NamedSchema",
    "TypeReference",
    "OverlayedDict",
    "SchemaAttribute",
    "Annotations",
    "Annotation",
    "NumberSchema",
    "IntegerSchema",
    "StringSchema",
    "BinarySchema",
    "BoolSchema",
    "ArraySchema",
    "ObjectSchema",
    "PseudoTag",
    "EnumSchema",
    "ValueSchema",
    "BagSchema",
    "UnaryOpSchema",
    "ExtractorSchema",
    "ExponentSchema",
    "EmptySchema",
    "IndefSchema",
    "types",
    "schemata",
]
# 組み込み・デフォルト定義のスキーマ群
types = {
    'integer': IntegerSchema(),
    'number': NumberSchema({}),
    'string': StringSchema({}),
    'binary': BinarySchema({}),
    'boolean': BoolSchema({}),
    'array': ArraySchema([UnivSchema()], options={'repeat': True}),
    'object': ObjectSchema(schema_obj={}, wildcard=UnivSchema({})),
    'any': AnySchema({}),
    'null': NullSchema({}),
    'void': VoidSchema({}),
    'never': NeverSchema({}),
    'bag': BagSchema([]),
    'undefined': OptionalSchema(UndefinedSchema()),
    'univ': UnivSchema({}),
    'indef': IndefSchema({}),
    'foreign': ForeignSchema({}),
}

schemata = types # とりあえず互換性維持のために残しておく

