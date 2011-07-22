#coding: utf-8

name = u'debug'
schema = u"""
/**
 * 入力値を標準出力に書き出す。それ以外の動作は pass と同じ。
 */
command dump<T> :: T -> T
    refers python:caty.core.std.command.debug.Dump;

/**
 * セッションの値をすべて出力する。
 */
 command dump-session :: void -> object
    reads session
    refers python:caty.core.std.command.debug.DumpSession;

/**
 * セッションから指定されたキーの値を取得する。
 * nullable オプションが指定された場合、キーが見つからなかったときに null を返す。
 */
 command get-session<T> {"nullable": boolean?} [string] :: void -> T
    reads session
    refers python:caty.core.std.command.debug.GetSession;

/**
 * スキーマ定義のダンプ
 */
command dump-schema [string] :: void -> void
    reads [interpreter, schema]
    refers python:caty.core.std.command.debug.DumpSchema;

/**
 * メモリ使用状況のプロファイルを行う。
 * このコマンドを使うにはguppy (http://pypi.python.org/pypi/guppy)が必要となる。
 */
command profile {"tree": boolean?} :: void -> string
    refers python:caty.core.std.command.debug.Profile;
    """
