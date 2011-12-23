#coding: utf-8

name = u'filter'
schema = u"""
/**
 * 入力値がnullまたは未定義でなければtrue, nullであればfalseを返す。
 *
 */
@[filter]
command notnull :: any -> boolean
    refers python:caty.core.std.command.filtercmd.NotNullFilter;

/**
 * 入力値が空文字、空リスト、空オブジェクト、null、未定義値でなければtrue, そうであればfalseを返す。
 *
 */
@[filter]
command notempty :: any -> boolean
    refers python:caty.core.std.command.filtercmd.NotEmptyFilter;

/**
 * 入力値が空文字、空リスト、空オブジェクト、null、未定義値でなければfalse, そうであればtrueを返す。
 *
 */
@[filter]
command empty :: any -> boolean
    refers python:caty.core.std.command.filtercmd.EmptyFilter;

/**
 * 入力値を引数で割ったその余りを返す。
 */
@[filter]
command mod [string] :: any -> any
    refers python:caty.core.std.command.filtercmd.ModuloFilter;

/**
 * 入力値と引数が等しいかを返す。
 */
@[filter]
command eq [string] :: any -> boolean
    refers python:caty.core.std.command.filtercmd.EqFilter;

/**
 * 入力値と引数が異なっているかを返す。
 */
@[filter]
command ne [string] :: any -> boolean
    refers python:caty.core.std.command.filtercmd.NotEqFilter;

/**
 * 入力値の否定を返す。
 */
@[filter]
command not :: any -> boolean
    refers python:caty.core.std.command.filtercmd.NotFilter;

/**
 * 入力が未定義値でなければtrueを返す。
 */
@[filter]
command defined :: any -> boolean
    refers python:caty.core.std.command.filtercmd.DefinedFilter;

/**
 * 文字列をエスケープしないようにテンプレートエンジンに伝える。
 */
@[filter]
command noescape :: any -> any
    refers python:caty.core.std.command.filtercmd.RawStringFilter;

/**
 * 入力がオブジェクト型かどうかを判定する。
 */
@[filter]
command isobject :: any -> boolean
    refers python:caty.core.std.command.filtercmd.IsObject;

/**
 * 入力が配列型かどうかを判定する。
 */
@[filter]
command isarray :: any -> boolean
   refers python:caty.core.std.command.filtercmd.IsArray;

/**
 * 入力値を文字列化する。
 */
@[filter]
command json :: any -> string {json:pretty};

/** JSONデータをエスケープせずにシリアライズする。
 * このフィルターの出力は、そのままJavaScriptコード内で利用できる。
 * JavaScriptコード以外では使用すべきではない。
 * pre要素内部などにJSONデータを展開したいときは、
 * エスケープを行うjsonフィルターを使用すべきである。
 */
@[filter]
command javascript :: any -> any {json:pretty|noescape};


"""
