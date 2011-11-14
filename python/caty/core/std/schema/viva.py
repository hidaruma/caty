#coding: utf-8

name = u'viva'
schema = u"""
/** 
 * アクションモジュール（.caraファイル）を視覚化する。
 */
command draw {
 /** 出力ファイル
  * 指定がないときは標準出力
  */
 "out" : string(remark="Catyのファイルパス")?, 

 /** 出力フォーマット */
 @[default("gif")]
 "format" : ("gif" | "png" | "jpeg" | "dot" | "svg" | "svge")?,

 /** 図示するノード */
 @[default("any")]
 "node" : ("state" | "action" | "any")?,

 /** ファイル出力時に.caraの変更がされていない場合は再出力しない */
 @[with("out"), default(false)]
 "if-modified": booelan?,

 /** 描画に使われるフォント。日本語を使う場合は指定するのを推奨 */
 "font": string?
} [
  /** モジュール名
   * 拡張子は含まない
   */
  string module
] :: void -> void | binary | string
     throws [ModuleNotFound]
     updates pub
    refers python:caty.core.std.command.viva.DrawModule;

/** 
 * アクションモジュール（.caraファイル）の個別アクションを視覚化する。
 */
command draw-action {
 /** 出力ファイル
  * 指定がないときは標準出力
  */
 "out" : string(remark="Catyのファイルパス")?, 

 /** 出力フォーマット */
 @[default("gif")]
 "format" : ("gif" | "png" | "jpeg" | "dot" | "svg" | "svge")?,
 
 /** アクション内のコードフラグメントと入出力型のみを描く */
 @[default(false)]
 "lone": boolean?,

 /** ファイル出力時に.caraの変更がされていない場合は再出力しない */
 @[with("out"), default(false)]
 "if-modified": booelan?,

 /** 描画に使われるフォント。日本語を使う場合は指定するのを推奨 */
 "font": string?
} [
  /** モジュール名:リソース名.アクション名 */
  string action_name
] :: void -> void | binary | string
     throws [ModuleNotFound, ResourNotFound, ActionNotFound]
     updates pub
    refers python:caty.core.std.command.viva.DrawAction;

type GraphStruct = {
    "name": string,
    "subgraphs": [GraphStruct*],
    "nodes": [Node*],
    "edges": [Edge*],
};

type Node = {
    "name": string,
    "label": string,
    "type": "action" | "state"
};

type Edge = {
    "trigger": string?,
    "from": string?,
    "to": string?,
    "type": "link" | "action",
};
"""
