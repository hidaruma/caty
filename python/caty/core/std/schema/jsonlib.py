#coding: utf-8

name = 'json'
schema = u"""
type AnyObject = {*:any};
type StandardJson = string | integer | number | null | boolean | array | object;

/** selectionのフォーマットや値に間違いがある */
exception BadSelection = object;

type selection = {
 /** 選択の方式、必須とする */
 "$selection" : ("array"|"object"),
 /** 現在の値の番号または名前 */
 "$current" : integer(minimum=0) | string,
 /** 値の候補 */
 "$values" : [any*] | {*:any?}
};

/**
 * 引数で指定されたファイルを JSON データとして読み込み、値を返す。
 * JSON でないデータの書き込まれたファイルに対しての動作は保証しない（通常はエラー）。
 */
command read [string] :: void -> any
    reads [pub, data]
    refers python:caty.core.std.command.jsonlib.ReadJson;

/**
 * 引数で指定されたファイルに JSON データを書き込む。
 * このコマンドで書き込んだデータは json:read で読み出し可能である。
 */
command write [string] :: any -> void
    updates [data, pub]
    refers python:caty.core.std.command.jsonlib.WriteJson;

/**
 * 入力値の JSON オブジェクトを整形して返す。
 */
command pretty :: any -> string
    refers python:caty.core.std.command.jsonlib.Pretty;

/**
 * 二つの object をマージする。
 * --mode オプションではプロパティ名が衝突した場合の解消方法を指定する。
 *
 * * "fst": 第一要素のものを用いる
 * * "snd": 第二要素のものを用いる
 * * "error": エラーとして扱い、 null を返す
 */
command merge {"mode": string?} :: [AnyObject, AnyObject] -> AnyObject | null
    refers python:caty.core.std.command.jsonlib.Merge;

/**
 * 入力値を application/json フォーマットで出力する。
 */
command response {"status": integer?, "encoding": string?} :: StandardJson -> Response
    refers python:caty.core.std.command.jsonlib.JsonResponse;

/**
 * 入力値文字列をパースして、JSONオブジェクトを出力する。
 */
command parse :: string -> any
    reads env
    refers python:caty.core.std.command.jsonlib.Parse;

/** 入力データのselectionを確定値に直して出力 */
command fix-on-selection :: any -> any
    throws BadSelection
    refers python:caty.core.std.command.jsonlib.FixOnSelection;

"""
