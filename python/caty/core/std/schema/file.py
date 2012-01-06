#coding: utf-8

name = 'file'
schema = u"""
type DirectoryEntry = {"name":string, "isDir":boolean, *:any};

/**
 * 引数で指定したファイル名で空のファイルを作成する。
 */
command zerofile [string] :: void -> @OK string
    uses [data, include, pub]
    refers python:caty.core.std.command.file.ZeroFile;

/**
 * 引数で指定したファイルが存在するかどうかを返す。
 */
command exists {@[default(false)]"pred": boolean?} [string] :: void -> @OK string | @NG string | boolean
    uses [data, include, pub]
    refers python:caty.core.std.command.file.Exists;

/**
 * 引数で指定したファイルを読み込み、その値を返す。ファイルがバイナリファイルの場合の動作は保証しない。
 */
command read [string] :: void -> string | binary
    reads [data, include, pub, behaviors, scripts, sysfiles]
    refers python:caty.core.std.command.file.ReadFile;

/**
 * 入力で指定したファイルを読み込み、その値を返す。ファイルがバイナリファイルの場合の動作は保証しない。
 */
command read-i [] :: string -> string | binary
    reads [data, include, pub, behaviors, scripts]
    refers python:caty.core.std.command.file.ReadFileI;

/**
 * 引数で指定したファイルに入力値を書き込む。
 */
command write [string] :: string -> void
    updates [data, include, pub]
    refers python:caty.core.std.command.file.WriteFile;

/**
 * 引数で指定したファイルまたはディレクトリを削除する。
 */
command delete [string] :: void -> null
    updates [data, include, pub]
    refers python:caty.core.std.command.file.DeleteFile;

/**
 * 引数で指定したファイルの最終更新時刻を取得する。
 */
command lastmodified [string] :: void -> string
    reads [data, include, pub, behaviors, scripts]
    refers python:caty.core.std.command.file.LastModified;

/**
 * 引数で指定したファイルの実際のファイルシステム上の絶対パスを返す。
 * mafs のバックエンドが実際のファイルシステムでない場合、引数がそのまま返される。
 */
command realpath [string] :: void -> string
    reads [data, include, pub, behaviors, scripts]
    refers python:caty.core.std.command.file.RealPath;

/**
 * ディレクトリを作成する。
 */
command mkdir [string] :: void -> void
    updates [pub, include, data, behaviors, scripts]
    refers python:caty.core.std.command.file.MakeDir;

/**
 * ディレクトリ一覧の表示。
 *
 * 第一引数で指定されたディレクトリを読み込み、配下のファイルとディレクトリ一覧を返す。
 * 第二引数は拡張子の指定であり、例えば .html が指定された場合 .html 拡張子のファイル一覧だけが返される。
 * 通常はファイル名とファイルかディレクトリの種別のみが返されるが、
 * --long オプションが指定された場合は最終更新時刻なども返される。
 */
command list {"long":boolean?, "kind":string?} [string, string?] :: 
    void -> [DirectoryEntry*]
    reads [pub, data, scripts, include, sysfiles]
    refers python:caty.core.std.command.file.LsDir;

"""
