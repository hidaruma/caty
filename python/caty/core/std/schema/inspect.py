#coding: utf-8
name = u'inspect'
schema = u"""
type typeExprText = string(remark="型表現のテキスト");
type exceptionName = string(remark="例外の名前");


/** コマンドプロファイル情報の簡易版 */
type ShortProfile = {
 /** コマンドの名前 */
 "name" : string,

 /** コマンドの型引数
  * コマンドが多相IOプロファイルを持つとき、束縛型変数（名前文字列）のリストを指定する。
  * IOプロファイルが具体的（単相）なときは空配列。
  */
 "typeVars" : [string*],

 /** 実装状況 */
 "implemented" : implemented?,

 /** オプションの型 */
 "opts" : typeExprText,

 /** 引数の型 
  * arg0は含まれないので、args[0]がargv[1]であることに注意
  */
 "args" : typeExprText,

 /** 入力の型 */
 "input" : typeExprText,

 /** 出力の型 */
 "output" : typeExprText,

 /** 例外の型 */
 "throws" : ([exceptionName*] | @only [exceptionName*])?,
};
/** 実装状況を示す値 
 */
type implemented = (
  /** 実装はない、宣言されているだけ */
  "none" |

  /** Python実装を持つ */
  "python" |

  /** CatyScript実装を持つ */
  "catyscript" |
);
/** モジュールに含まれるコマンドを列挙する
 * 引数に指定されたモジュールに固有なコマンドだけを列挙する。
 * 別名として存在するコマンドや、そのモジュールから可視な別モジュールのコマンドは列挙しない。
 * 
 * モジュール名はパッケージ修飾を許す。
 * またアプリケーション名で修飾してもよい。
 * 例：
 *  * mymod
 *  * pkg.mymod
 *  * otherapp:somepkg.yourmod
 *  * this:pkg.mymod
 */
command list-cmd 
 {
   /** 当面、shortオプションのデフォルトはtrue */
   @[default(true)]
   "short" : boolean?,
 }
 [string moduleName] :: void -> [ShortProfile*]
 throws ModuleNotFound
 refers python:caty.core.std.command.inspect.ListCommands;
"""
