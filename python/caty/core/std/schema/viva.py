#coding: utf-8

name = u'viva'
schema = u"""
/** 
 * アクションモジュール（.caraファイル）を視覚化する
 */
command draw {
 /** 出力ファイル
  * 指定がないときは標準出力
  */
 "out" : string(remark="Catyのファイルパス")?, 

 /** 出力フォーマット */
 @[default("png")]
 "format" : ("gif"|"png"|"jpeg" | "dot")?,

 /** 図示するノード */
 @[default("state")]
 "node" : ("state" | "action" | "any")?,

} [
  /** モジュール名
   * 拡張子は含まない
   */
  string module
] :: void -> void | binary 
     throws [ModuleNotFound]
     updates pub
    refers python:caty.core.std.command.viva.Draw;

type GraphStruct = {
    "name": string,
    "subgraphs": [GraphStruct*],
    "nodes": [Node*],
    "edges": [Edge*],
};

type Node = {
    "name": string,
    "type": "action" | "state"
};

type Edge = {
    "trigger": string?,
    "from": string?,
    "to": string?
};

/**
 * .caraモジュールのアクション及びステートのグラフ構造のダンプ。
 */
command dump-struct {
    @[default("state")] "node": ("state" | "action" | "any")?,
    @[default("dot")] "format": "dot" | "internal",
    } [string module] :: void -> void
     throws [ModuleNotFound]
    refers python:caty.core.std.command.viva.GraphStruct;
    

"""
