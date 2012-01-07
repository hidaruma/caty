#coding: utf-8
name = u'os'
schema = u"""
/** OSのシェルスクリプトを実行する。
 * 実行したいシェルスクリプトファイルは、Catyの scripts/ の下に置く。
 * script-nameには、scripts/ からの相対パスで拡張子を含む名前を指定する。
 * Windowsでは、.bat, .cmdなどの拡張子が必須、Unixでも .sh を推奨。
 * 指定したシェルスクリプトファイルが存在しないなら、ScriptNotFound例外。
 * なんらかの事情でシェルスクリプトが実行できないときは、CommandExecutionError例外。
 * 出力は、OSのプロセス終了ステータスの整数値。
 */
command exec-script [string script-name, string* args] :: void -> integer
 throws [ScriptNotFound, CommandExecutionError]
 reads scripts
 refers python:caty.core.std.command.oslib.ExecScript;

/** 整数値の終了ステータスを OK, NG タグ付きデータに変換する。
 * 0はOK、その他の値はNGとなる。
 */
command status :: integer -> (@OK integer | @NG integer)
 refers python:caty.core.std.command.oslib.Status;

/** OSプラットフォームの種類を表す文字列を返す。*/
command platform :: void -> ("Linux" | "Windows" | "Java")
 refers python:caty.core.std.command.oslib.Platform;
"""
