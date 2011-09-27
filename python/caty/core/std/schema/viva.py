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
 "format" : ("gif"|"png"|"jpeg" | "dot")?,

 /** 図示するノード */
 @[default("any")]
 "node" : ("state" | "action" | "any")?,

 /** グラフのサイズ(インチで指定、!を付けるとサイズ強制) */
 @[default("auto"), typical("6.4!, 4.8")]
 "size": string?,

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
 "format" : ("gif"|"png"|"jpeg" | "dot")?,
 
 /** アクション内のコードフラグメントと入出力型のみを描く */
 @[default(false)]
 "lone": boolean?,
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
