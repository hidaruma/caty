#coding: utf-8

name = 'text'
schema = u"""
type RegexpMatch = {
    "src": string,
    "group": string,
    "groups": [string*],
};

/**
 * 入力値の先頭と末尾から空白と改行を除去して返す。
 */
command chop :: string -> string
    refers python:caty.core.std.command.text.Chop;

/**
 * 入力値の先頭と末尾から引数の文字を除去して返す。
 */
command trim [string] :: string -> string
    refers python:caty.core.std.command.text.Trim;

/**
 * 入力値を creole 記法の Wiki テキストだとみなし、 HTML に変換して返す。
 * このコマンドは後方互換性及び簡易的なアプリケーションのためにのみ存在する。
 * 応用的な理容には creole モジュールと xjx モジュールを使用すること。
 */
command creole :: string -> string
    refers python:caty.core.std.command.text.Creole;

/**
 * 引数を区切り文字として入力値を連結して返す。
 */
command join [string]:: [string*] -> string
    refers python:caty.core.std.command.text.Join;

/**
 * 入力値を連結して返す。
 */
command concat :: [string*] -> string
    refers python:caty.core.std.command.text.Concat;

/**
 * 入力値を大文字にして返す。
 */
command toupper :: string -> string
    refers python:caty.core.std.command.text.ToUpper;

/**
 * 入力値を小文字にして返す。
 */
command tolower :: string -> string
    refers python:caty.core.std.command.text.ToLower;

/**
 * 入力値を引数の文字列で分割して返す。
 * 第二引数が与えられた場合、それ+1が分割数の最大値となる。
 */
command split [string] :: string -> [string*]
              [string, integer] :: string -> [string*]
    refers python:caty.core.std.command.text.Split;

/**
 * 入力値を引数の文字列で分割して返す。
 * 第二引数が与えられた場合、それ+1が分割数の最大値となる。
 * text:split との差異は、こちらは文字列を末尾から分割していく事である。
 */
command rsplit [string] :: string -> [string*]
               [string, integer] :: string -> [string*]
    refers python:caty.core.std.command.text.RSplit;

/**
 * 入力値の HTML を整形式の XHTML に修正する。
 *
 */
command correct-html :: string | {*:any} -> string | {*:any}
    reads env
    refers python:caty.core.std.command.text.CorrectHTML;

/**
 * 入力文字列が引数の正規表現パターンに合致するかどうかを返す。
 * 合致していれば @matched タグの付いたオブジェクトが返り、
 * 合致していなければ @fail タグの付いた入力文字列が返る。
 */
command regmatch [string] :: string -> @match RegexpMatch | @fail string
    refers python:caty.core.std.command.text.RegMatch;
"""
