#coding: utf-8
name = u'gv'
schema = u"""
/** 色の名前、または数値指定 
 * [[http://www.graphviz.org/content/attrs#kcolor]]
 */
type color  = deferred string(remark="color description");

/** ノードの形状名
 * [[http://www.graphviz.org/content/attrs#kshape]]
 */
type shape  = deferred string(remark="shape name");

/** ノードのスタイルの値 
 * [[http://www.graphviz.org/content/attrs#kstyle]]
 */
type nodeStyle  = deferred string(remark="node style value");

/** 辺のスタイルの値 
 * [[http://www.graphviz.org/content/attrs#kstyle]]
 */
type edgeStyle  = deferred string(remark="edge style value");


/** グラフのスタイルの値 
 * [[http://www.graphviz.org/content/attrs#kstyle]]
 */
type graphStyle = deferred string(remark="graph style value");

/** 矢印の形状の名前 
 * [[http://www.graphviz.org/content/attrs#karrowType]]
 */
type arrowType = deferred string(remark="arrow type");

/** エスケープシーケンスを許す文字列
 * [[http://www.graphviz.org/content/attrs#kescString]]
 */
type escString = string(remark="string allowing escape sequences");

/** ラベル文字列
 * [[ http://www.graphviz.org/content/attrs#klblString]]
 */
type lblString = string(remark="escString or an HTML label");

/** グラフ、ノード、辺、クラスターに付けるID */
type elementId = string;

/** Graphvizで使える属性名 */
type AttrName = string(pattern="[a-zA-Z][a-zA-Z0-9]*");

/** 属性の一般的な形式 */
type Attributes = {
 "id": undefined,
 "nodes" : undefined,
 * : (number|string|boolean)?
}(propNameFormat="gv-attr-name") ;

/** ノードの属性 */
type NodeAttributes = Attributes & {
 "color"     : color?,
 "fillcolor" : color?,
 "fontcolor" : color?,
 "label"     : lblString?,
 "shape"     : shape?,
 "style"     : nodeStyle?,

 // まだ実験的なので拡張を許す
 *          : (number|string|boolean)?
};

/** 辺の属性 */
type EdgeAttributes = Attributes & {
 "arrowhead" : arrowType?,
 "arrowtail" : arrowType?,
 "color"     : color?,
 "fontcolor" : color?,
 "headlabel" : lblString?,
 "label"     : lblString?,
 "style"     : edgeStyle?,

 // まだ実験的なので拡張を許す
 *          : (number|string|boolean)?
};

/** グラフの属性 */
type GraphAttributes = Attributes & {
 @[default("X11")]
 "colorscheme" : ("X11" | "SVG" | "Brewer")?,

 "bgcolor"   : color?,
 "color"     : color?,
 "fillcolor" : color?,
 "fontcolor" : color?,
 "label"     : lblString?,
 "style"     : graphStyle?,

 // まだ実験的なので拡張を許す
 *          : (number|string|boolean)?
};

/** クラスターの属性 */
type ClusterAttributes = GraphAttributes;

/** 有向グラフ */
type Digraph = @digraph {
 "id" : elementId,

 /** このグラフ全体の属性 */
 "graph" : GraphAttributes?,

 /** ノードのデフォルト属性 */
 "node"  : NodeAttributes?,

 /** 辺のデフォルト属性 */
 "edge"  : EdgeAttributes?,

 /** グラフを構成するノード、辺、クラスター */
 "elements" : [(Node | Edge | Cluster)*]
};

/** ノード
 * 属性が不要なときは、IDとなる文字列だけでよい。
 */
type Node = @node (elementId | NodeObj);

/** ノードを表現するオブジェクト
 * id以外のプロパティはノード属性。
 */
type NodeObj = NodeAttributes ++ {
 "id" : elementId
};

/** 辺のターゲット
 * 複数のノードIDを指定してもよい。
 */
type Target = (elementId | [elementId, elementId, elementId*]);

/** 辺
 * 属性が不要なときは、ノードIDの組み合わせだけでよい。
 */
type Edge = @edge ([elementId, Target] | EdgeObj);


/** 辺を表現するオブジェクト
 * id, nodes以外のプロパティは辺属性。
 */
type EdgeObj = EdgeAttributes ++ {
 "id" : elementId?,
 "nodes" : [elementId, Target]
};

/** クラスター（特殊なサブグラフ） */
type Cluster = @cluster {
 /** クラスターID
  * このIDに "cluster" が前置されてサブグラフのIDとなる。
  */
 "id" : elementId,

 /** このサブグラフ全体の属性 */
 "graph" : GraphAttributes?,

 /** ノードのデフォルト属性 */
 "node"  : NodeAttributes?,

 /** 辺のデフォルト属性 */
 "edge"  : EdgeAttributes?,

 /** サブグラフを構成するノード、辺、クラスター */
 "elements" : [(Node | Edge | Cluster)*]
};

/** Catyのファイルパス */
type filePath = string(remark="Catyのファイルパス");

/** Graphvizのレイアウトエンジン名 */
type layoutEngine = ("dot" | "neato" | "fdp" | "sfdp" | "twopi" | "circo");

/** Graphvizの出力フォーマット名 */
type outputFormat = ("gif" | "png" | "jpeg" | "dot" | "svg" | "svge");

/** 有向グラフの描画 */
command draw 
 {
  /** 出力フォーマット */
  @[default("gif")]
  "format": outputFormat?,

  /** レイアウトエンジン */
  @[default("dot")]
  "engine": layoutEngine?,
 
  /** 描画に使われるフォント。日本語を使う場合は指定するのを推奨 */
  "font": string(remark="フォント名")?,
 
  /** 出力ファイル
   * 指定がないときは標準出力
   */
  "out": filePath?,

  /** データ最終変更の日時 */
  @[without("timefile")]
  "time" : common:dateTime?,

  /** このファイルのタイムスタンプをデータ最終変更の日時とみなす 
   * ファイルが存在しないときは、そのタイムスタンプは無限の未来だとする。
   */
  @[without("time")]
  "timefile" : filePath?,

  /** 出力ファイルがデータ最終変更の日時より古いときだけ描画する */
  @[with(@_OR ["time", "timefile"]), default(false)]
  "if-modified" : boolean?
  
 }
 :: Digraph -> (void | binary | string) ;

/** 空なグラフのデータ */
command empty-graph :: void -> Digraph {
  @digraph {
    "id" : "empty-graph",
    "elements" : []
  }
};

/** 引数で指定されたファイルのグラフデータを描画する */
command draw-from-file 
 {
  /** 出力フォーマット */
  "format": outputFormat?,

  /** レイアウトエンジン */
  "engine": layoutEngine?,
 
  /** 描画に使われるフォント。日本語を使う場合は指定するのを推奨 */
  "font": string(remark="フォント名")?,

  /** 出力ファイル
   * 指定がないときは標準出力
   */
  "out": filePath?,

  /** 出力ファイルが入力ファイルより古いときだけ描画する */
  "if-modified" : boolean?
 }
 [/** グラフデータが格納されたファイル */ filePath file]
 :: void  -> (void | binary | string) 
{ 
  %1 > file;
  file:exists %file |
  when {
    NG => empty-graph,
    OK => xjson:read %file
  } | draw --timefile=%file %--format %--engine %--font %--out %--if-modified 
};

"""

