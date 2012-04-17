#coding: utf-8

name = u'fit'
schema = u"""

/**
 * CatyFITの実行。
 * 引数にファイル名が指定された場合、単一のビヘイビアファイルを実行する。
 * 引数にディレクトリ名が指定された場合、そのディレクトリに属するビヘイビアファイルを実行する。
 * 引数が指定されなかった場合、すべてのビヘイビアファイルを実行する。
 * forceオプションが指定された場合、明示的に補足しなかった例外を補足し、
 * エラーではなく失敗として扱う。
 * debugオプションが指定された場合、実行されるコマンドラインを表示しながら実行する。
 *
 * CatyFITはデフォルトではdry runでテストを行う。
 * 即ちあらゆるファシリティへの書き込み要求のトランザクションはテスト終了時に破棄される。
 * 実際にファイルシステムやデータベースへの書き込みを行ったテストを行いたい場合、
 * no-dry-runオプションを付けて実行すること。
 */
command run {
    @[default(false)]
    "debug": boolean?,

    @[default(false)]
    "force": boolean?,

    @[default(false)]
    "verbose": boolean?,

    @[default(false)]
    "no-dry-run": boolean?,

    /** 検索するファイルの拡張子 */
    @[default(".beh")]
    "ext" : behExt?,

    /** ファイルの検索を再帰的に行うかどうか */
    @[default(false)]
    "rec" : boolean?,

    /** 処理結果の出力ファイル */
    @[without("outdir")]
    "out" : mafsPath?,

    /** 処理結果の出力ディレクトリ */
    @[without("out")]
    "outdir" : mafsPath?,

    /** すべてのアプリケーションを対象にする
     * このオプションを指定するときは、
     * 引数と、ext/rec/out/outdirオプションは指定できない。
     */
    @[default(false), without(["out", "ext", "outdir"])]
    "all-apps": boolean?,
  }
  [string? path] :: void -> void
        reads [env, behaviors, sysfiles]
        uses [pub, interpreter, stream]
        refers python:caty.core.std.command.fit.Run;

type mafsPath = string(remark="プレース修飾を許すパス名、末尾がスラッシュならディレクトリ");

type behExt = (
  ".beh"|".wiki"|".lit" |
  "beh" |"wiki" |"lit" |
);

/**
 * ビヘイビアファイル一覧の出力。
 */
command list :: void -> void
    reads behaviors
    updates stream
    uses interpreter
    refers python:caty.core.std.command.fit.List;

/**
 * CatyFITの結果の削除。
 * デフォルトではビヘイビアファイルよりも古い結果ファイルをすべて削除する。
 * --allを指定することで、すべての結果ファイルを削除できる。
 *
 * ファイルあるいはディレクトリ名を引数に指定することも可能である。
 * ファイル名を引数に指定した場合、そのファイルに対応した結果ファイルを削除する。
 * ディレクトリ名を指定した場合、そのディレクトリ配下に対して前節の動作を行う。
 *
 * --all-appsオプションが与えられた場合、全てのアプリケーションの結果ファイルの削除を行う。
 * --allオプションの扱いは同様であるが、引数のディレクトリ名は無視される。
 */
command clean {"all": boolean?, "all-apps":boolean?} [string?] :: void -> void
    uses [pub, behaviors]
    reads env
    refers python:caty.core.std.command.fit.ClearReport;

/**
 * CatyFITの結果のレポート。
 * CatyFITの実行結果ファイルを調べ、NG, Indef, Errorがあった場合、
 * それを標準出力に書き出す。
 * デフォルトでは起動元のアプリケーションの実行結果を走査するが、
 * --allが指定された場合すべてのアプリケーションの実行結果だけを走査する。
 */
command report {"all": boolean?} :: void -> void
    reads [env, pub]
    refers python:caty.core.std.command.fit.SendReport;

"""
