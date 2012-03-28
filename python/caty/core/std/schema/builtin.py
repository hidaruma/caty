#coding: utf-8

schema = u"""
type CatyExecMode = [string*];

type DirectoryEntry = {"name":string, "isDir":boolean, *:any};

type ErrorObj = {
    "isError": boolean,
    "orig": string,
    "val": any,
    "message": string,
    "errorId": string?,
    "param": {*:any}?,
    *: any
};

type pinteger = integer(minimum=0);

type ErrorItem = ErrorObj & {
    "name": string,
    *: any
};

type ErrorList = [ErrorItem*];

type ErrorMap = {
    *: ErrorObj
};

type ErrorInfo = {
    "errorList": ErrorList,
    "errorMap": ErrorMap
};

type MiniErrorInfo = MiniErrorObj | MiniError;

type MiniErrorObj = {
    *: string
};

type MiniError = string;

type WebInput = FormInput | JsonInput | @form FormInput;

// 本当は @form とすべきだろうが使い勝手を考えて
type FormInput = {
    *: [WebItem, WebItem*]
};

type WebItem = any;

type JsonInput = @json any;

type Response = {
    "status": integer(minimum=200, maximum=299),
    "header": {
        "content-type": string?,
        "content-length": integer?,
        *: string
    },
    "body": string | binary,
    "encoding": string? // テキストデータを返すときは必ずこれを追加
};

type Redirect = {
    "status": integer(minimum=300, maximum=399),
    "header": {
        "Location": string,
        *: string
    }
};

type ErrorResponse = {
    "status": integer(minimum=400),
    "header": {
        "content-type": string?,
        "content-length": integer?,
        *: string
    },
    "body": string | binary,
    "encoding": string? // テキストデータを返すときは必ずこれを追加
};

type WebOutput = Response | Redirect | ErrorResponse;

type ErrorStatus = {
    "status": integer
};

type AppInfo = {
    "name": string,
    "description": string,
    "path": string,
    *:any
};

/**
 * Catyのアプリケーション毎の設定ファイル。
 */
type AppManifest = {

    /**
     * 実装言語(現時点ではpythonのみ)
     */
    @[default("python")]
    "implLang": string?,

    /**
     * アプリケーションの説明
     */
    "description": string?,

    /**
     * アプリケーションの無効化の設定
     */
    "disabled": boolean?,

    /**
     * ディレクトリの末尾に/の付いていないアクセスへの対応。
     * "redirect"を設定すると/の付いたアドレスにリダイレクトされる。
     * "dont-care"では404 Not Foundとなる。
     */
    @[default("redirect")]
    "missingSlash": ("redirect" | "dont-care")?,
    
    /**
     * ファイルタイプとアソシエーションの設定。
     */
    "filetypes": {
        *: FileType ++ {"assoc": Assoc?}
    }?,

    /**
     * アプリケーション固有情報。
     */
    "appProp": CatyAppProperty?,

    /**
     * pub, dataなどのデータの設定。
     */
    "assign": {
        *:string,
    }?,
    *:any
};

/**
 * Caty全体の設定ファイル。
 */
type GlobalConfig = {
    /**
     * プロジェクト名。省略時はカレントディレクトリの名前が設定される。
     */
    "projectName": string?,
    /**
     * mafs実装のモジュール名
     */
    "mafsModule": string,

    /**
     * Catyのスタンドアローンサーバのモジュール名
     */
    "serverModule": string,

    /**
     * セッションの設定
     */
    "session": {
        /**
         * セッションのタイプ。"memory"のみ現在は対応。
         */
        "type": string,

        /**
         * セッションの保持される期間
         */
        "expire": integer,
    },

    /**
     * パスワード生成などでsaltの一部に用いる文字列
     */
    "secretKey": string,

    /**
     * システム全体のエンコーディング
     */
    "encoding": string,

    /**
     * Webサーバのアドレス(/は末尾に付けない)
     */
    "hostUrl": string,
    
    /**
     * システムの言語コード
     */
    "language": string,

    /** true にすると Caty スクリプトのコンパイル結果をキャッシュ */
    "enableScriptCache": boolean, 
    
    /** true にすると HTTP メソッドトンネリングが有効になる */
    "enableHTTPMethodTunneling": boolean, 

    /**
     * マルチスレッドの代わりにマルチプロセスを使うかどうか
     * マルチプロセス使用不可の環境では、マルチスレッドにフォールバックされる。
     */
    "useMultiprocessing": boolean, 
    
    /** 
     * Caty アプリケーションとして扱わないディレクトリ名のリスト。デフォルトは["CVS"]
     */
    "ignoreNames": [string*]?, 

    /**
     * アクセス可能なIPアドレスのリスト(末尾のみワイルドカード可)。
     * 特に指定されなかった場合、全てのホストからのアクセスを受け付ける
     */
    "addrsAllowed": [string*]?,

    /**
     * アクセスを拒否するIPアドレスのリスト(末尾のみワイルドカード)
     */
    "addrsDenied": [string*]?,


};

type Assoc = {
    // プロパティ名はverb名、デフォルトのverb名（無名）は""
    *:string
};

type Assocs = {
    *: Assoc
};

type FileType = {
    "isText": boolean?,
    "contentType": string?,
    "description": string?
};

type FileTypes = {
    *: FileType
};

type UploadFile = {
    "filename": string,
    "data": binary
};

// Catyの例外データは次の型のサブタイプでなくてはならない
// 実装言語の例外を直接投げることも禁止しない（禁止できない）

/** 人間可読なメッセージ */
type Message = {
  // プロパティ名は言語識別子, ja, en など
  * : string?
} (minProperties = 1);

type CatyException = @* {
 "message" : Message, 

 // 以下の2つのプロパティは、必要なら分類に使用する
 "class" : string?,
 "id" : (integer|string)?,

 // 実装言語のスタックトレースデータ
 "stackTrace" : any?,
 
  *: any?
};

/**
 * マニフェストにおけるアプリケーション固有情報
 */
type CatyAppProperty = {
    "$typename": string,
    "$callback": string?,
    *: any
};

/**
 * 組み込み型の名前
 */
type BuiltinTypeName = (
   "number" | "string" | "boolean" | "null" | "binary" // スカラー型
 | "array" | "object" // 複合型
 | "tagged"  // XJSONによる拡張
 | "unknown" // 不明
);

type typeName = string(remark="type-name");
type uri = string(remark="uri");
type mediaType = string(remark="media-type");
type httpMethod = ("GET" | "PUT" | "POST" | "DELETE" | "HEAD");

type Trigger = {
 // 個々のトリガーを識別する属性
 "id" : string?,
 "name" : string?,
 "class" : string?,

 // 説明的な情報
 "title" : string?,
 "help" : string?,

 // ハイパーリンクの記述
 "href" : uri,   // hrefは必須
 "rel" : string?,
 "rev" : string?,
 "type" : mediaType?,

 "enctype" : mediaType?,
 @[default("GET")]
 "method" : httpMethod?,

 // 手続き呼び出し的なデータ項目
 @[default("")]
 "verb" : string?,
 @[default("void")]
 "inputDatatype": typeName?,
 "paramsDatatype" : typeName?,

 // その他いろいろ
  * : any?
};


type Anchor = Trigger & {
 "enctype" : undefined,
 "method" : "GET",
 "inputDatatype": "void",

  * : any?
};

type Form = Trigger & {
 @[default("application/x-www-form-urlencoded")]
 "enctype" : mediaType?,

  * : any?
};

type Exception = @*! {
 "message" : string, 

 // 以下の2つのプロパティは、必要なら分類に使用する
 /** 例外クラス */
 "class" : string?,
 /** 例外ID */
 "id" : (integer|string)?,

 /** 実装言語のスタックトレースデータ */
 "stackTrace" : any?,
 
  *: any?
};

/**********************
 ******** 例外 ********
 **********************/

/** 例外型が存在しない。*/
exception ExceptionNotFound = object;

/** モジュールが存在しない */
exception ModuleNotFound = {
  "moduleName": string,
  "moduleType": "cara" | "casm",
  "appName": string,
  *: any?
};

/** リソースが存在しない */
exception ResourceNotFound = {
  "moduleName": string,
  "resourceName": string,
  *: any?
};


/** 型が存在しない */
exception TypeNotFound = {
  "moduleName": string,
  "typeName": string,
  *: any?
};

/** コマンドが存在しない */
exception CommandNotFound = {
  "moduleName": string,
  "cmdName": string,
  *: any?
};

/** アクションが存在しない */
exception ActionNotFound = {
  "moduleName": string,
  "actionName": string,
  "resourceName": string,
  *: any?
};

/** ユーザーロールが存在しない */
exception UserroleNotFound = {
  "moduleName": string,
  "userrole": string,
  *: any?
};

exception ApplicationNotFound = {
  "appName": string,
  *: any?,
};

/** 配列のインデックスが範囲外、または不正である。*/
exception IndexOutOfRange = object;

/** オブジェクトのプロパティが存在しない、またはプロパティ名が不正である。*/
exception PropertyNotExist = object;

/** データが（事故や不注意で）壊れていると推測される。*/
exception MalformedData = object;

/** 構文エラーが存在する。パーシングが失敗した。*/
exception SyntaxError = object;

/** 型の妥当性検証に失敗した。*/
exception ValidatatonFailed = object;

/** 入力が（なんらかの意味で）不正である。*/
exception InvalidInput = object;

/** データの整合性を破壊するので許されない操作である。*/
exception ConsistencyViolation = object;

/** ルーズ配列である。 */
exception LooseArray = object;

/** 未定義である。 */
exception Undefined = object;

/** タグが存在しない。 */
exception TagNotExist = object;

/** 要求されたスクリプトが見つからない、存在しない。*/
exception ScriptNotFound = object;

/** 要求されたファイルが見つからない、存在しない。*/
exception FileNotFound = object;

/** ファイルのIOに関連してエラーが生じた。 */
exception FileIOError = object;


/** データベースのコレクションが見つからない。*/
exception CollectionNotFound = object;

/** コレクションへのアクセスに失敗。*/
exception CollectionAccessError = object;


/** 指定できないオプションが指定された。*/
exception UnexpectedOption = object;

/** オプションの値が不正である。*/
exception BadOption = object;


/** 引数が余分にある。*/
exception UnexpectedArg = object;

/** 引数が不足している。*/
exception MissingArg = object;

/** 引数の値が不正である。 */
exception BadArg = object;

/** 認証失敗 */
exception CertificationFailed = object;

/** 不正なアクセス */
exception IllegalAccess = object;

/** その他セキュリティエラー。 */
exception SecurityError = object;

/** コマンド実行エラー */
exception CommandExecutionError = object;

/** サポートされていない操作。 */
exception Unsupported = object;

/** タイムアウト。 */
exception Timeout = object;

/** 算術エラー。 */
exception ArithmeticError = object;

/** 実行時エラー。 */
exception RuntimeError = object;

/** 未実装。 */
exception NotImplemented =object;

/** 不明なエラー。*/
exception UnknownError = object;

/** 実装のバグ。 */
exception ImplementationBug = object;

/** コンパイルエラー */
exception CompileError = object;

/**
 * テンプレートを展開する際に扱われるデータ。
 * expand, printなどでテンプレートが展開される際、
 * 入力がobjectの場合はこの型のデータがプロパティとして追加される。
 * 入力がobjectでない場合は、入力を_CONTEXTの値としたobjectとなる。
 *
 */
type DefaultTemplateContext = {
    /** expand, printの引数のファイルパス */
    "_FILE_PATH": string,

    /** APP_PATH環境変数と同じ */
    "_APP_PATH": string,
    
    /** HOST_URL環境変数と同じ */
    "_HOST_URL": string,

    /** CATY_VERSION環境変数と同じ */
    "_CATY_VERSION": string,

    /** print, expandへの実際の入力 */
    "_CONTEXT": any,
    *: any?
};

/**
 * 入力値を標準出力に書き出す。それ以外の動作は pass と同じ。
 */
command dump<T default any> // 実は総称、passと同じだから
 {
  /** debugフラグに関わらず表示を強制する */
  @[default(false)]
  "force" : boolean?,

  /** 表示の先頭に付加する文字列 */
  @[default("")]
  "prefix" : string?,
 }
 :: T -> T
    refers python:caty.core.std.command.debug.Dump;

/**
 * 簡易的な print コマンド。
 *
 * print と同様の働きをするが、出力が HTTP 応答ヘッダのない単なる文字列となる。
 * コマンドラインシェルから起動する事を前提に作られている。
 * バイナリデータを読み込んだ場合、特に加工せずそのまま出力する。
 *
 */
command expand {"raw": boolean?, "no-script": boolean?, "resolve": boolean?, "mode":string?} [string filepath] :: 
    any -> string | binary
    uses [pub, env, include, interpreter]
    reads [schema]
    refers python:caty.core.std.command.builtin.Expand;

/*{{{
/** テンプレートをファイルからではなく文字列から取るexpand */
command expand_2 {"raw": boolean?, "no-script": boolean?, "resolve": boolean?, "mode":string?} :: 
    [any, string] -> string | binary
    uses [pub, env, include, interpreter]
    reads [schema]
    refers python:caty.core.std.command.builtin.Expand2;
    }}}*/

/**
 * 入力値を HTTP の応答ボディとし、 HTTP 応答ヘッダを付けて返す。
 * --ext オプションは拡張子の指定であり、このオプションが指定された場合は content-type ヘッダが対応した値となる。
 * 指定されなかった場合は application/octet-stream が用いられる。
 */
command response {"ext":string?, 
                  "status": integer?, 
                  "content-type": string?, 
                  "encoding": string?} :: string | binary -> Response
    reads [env, pub]
    refers python:caty.core.std.command.builtin.Response;

/**
 * 入力をテンプレートに対して適用し、 HTTP 応答ヘッダを付けて返す。
 *
 * --raw オプションが指定された場合、テンプレートを評価せずにそのまま返す。
 *
 * --resolve オプションが指定された場合、インライン/アウトオブラインスクリプトをテンプレートの入力として扱う。
 * 両者が同時に指定された場合、インラインスクリプトが優先して使用される。
 *
 * --mode オプションは text か html のどちらかを値としてとる。
 * text が指定された場合、 HTML 特殊文字の自動エスケープが働かなくなる。
 * デフォルトでは html が指定された状態であり、 Web ページの出力にはこちらを使う。
 * text はメールの文面の出力など、 Web ページの出力以外の場合に用いること。
 */
command print {"raw": boolean?, 
               "no-script": boolean?,
               @[default(true)]
               "resolve": boolean?, 
               "mode":string?} [string filepath] :: 
    any -> Response
    uses [pub, include, interpreter, env]
    reads [schema]
    refers python:caty.core.std.command.builtin.Print;

/**
 * Webアクセスをエミュレートする。
 * 
 *
 */
command request {
                "verb": string?, 
                "method": string?,
                "debug": boolean?,
                "fullpath": boolean?,
                "content-type": string?} [string path, string? query] :: WebInput | null -> WebOutput
    reads [env, schema]
    uses interpreter
    refers python:caty.core.std.command.builtin.Request;

/**
 * 引数で指定された型に入力値を変換して返す。
 */
command translate [string] :: WebInput -> @OK any | @NG MiniErrorInfo
    reads schema
    refers python:caty.core.std.command.builtin.Translate;

/**
 * 引数で指定された型で入力値を検証する。
 */
command validate {"pred":boolean?} [string] :: univ -> @OK univ | @NG MiniErrorInfo | boolean
    reads schema
    refers python:caty.core.std.command.builtin.Validate;

/**
 * 入力を捨てるコマンド。
 * 
 */
command void<T default univ> :: T -> void
  refers python:caty.core.std.command.builtin.Void;

/**
 * バージョン情報の表示。
 *
 */
command version :: void -> string 
  reads env
  refers python:caty.core.std.command.builtin.Version;

/**
 * ディレクトリ一覧の表示。
 *
 * 第一引数で指定されたディレクトリを読み込み、配下のファイルとディレクトリ一覧を返す。
 * 第二引数は拡張子の指定であり、例えば .html が指定された場合 .html 拡張子のファイル一覧だけが返される。
 * 通常はファイル名とファイルかディレクトリの種別のみが買えされるが、
 * --long オプションが指定された場合は最終更新時刻なども返される。
 */
command lsdir {"long":boolean?, "kind":string?} [string, string?] :: 
    void -> [DirectoryEntry*]
    reads pub
    refers python:caty.core.std.command.file.LsDir;

/**
 * 入力をそのまま出力にコピーする。
 *
 */
command pass<T default any> :: T -> T
    refers python:caty.core.std.command.builtin.PassData;

/**
 * 配列の n 番目のデータを返す。 item との違いはこちらは 1 始まりということである。
 */
command nth<T default any> [integer] :: @* [T*] -> T
    refers python:caty.core.std.command.builtin.Nth;

/**
 * 配列の添字 n のデータを返す。 nth との違いはこちらは 0 始まりということである。
 */
command item<T default any> [integer] :: @* [T*] -> T
    refers python:caty.core.std.command.builtin.Item;

/**
 * JSON オブジェクトから引数で与えられた名前のプロパティの値を取得する。
 * 値が存在しなかった場合は実行時エラーとなる。
 */
command pv<T default any> [string] :: @* object -> T
    refers python:caty.core.std.command.builtin.GetPV;

/**
 * JSON オブジェクトから引数で与えられた名前のプロパティの値を取得する。
 * 値が存在した場合 @EXISTS タグがついた値が返り、そうでなければ @NO タグのついた null が返る。
 */
command findpv<T default any> [string] :: object -> @EXISTS T | @NO null
        refers python:caty.core.std.command.builtin.FindPV;
    
/**
 * 二つの入力値の比較を行う。
 * 両者が同じであれば @Same タグ付きで値が返り、そうでなければ @Diff タグ付きで返る。
 *
 */
command eq :: [any, any] -> @Same any | @Diff [any, any]
    refers python:caty.core.std.command.builtin.Equals;

/**
 * 入力値二つのうち第一要素を Caty スクリプトの式、第二要素をその入力として実行する。
 * このコマンドはテストモードでしか動作しないため、通常は使う必要はない。
 */
@[test] command eval<T default any> :: [any, string] | string -> T
    uses interpreter
    refers python:caty.core.std.command.builtin.Eval;

/**
 * ディレクトリへのアクセスをindex.html, index.cgi, index.actに振り分ける。
 * このコマンドではverbを用いたアクセスをインデックスファイルに行えない。
 * もしもindex.htmlなどにverb付きアクセスをしたいのであれば、ディレクトリアクセスのアクションも書くこと。
 */
command dir-index [string path, string method] :: any -> any
    uses interpreter
    refers python:caty.core.std.command.builtin.DirIndex;

/**
 * 入力値のタグを取得する。組み込み型が与えられた場合、その型名がタグとして扱われる。
 */
command tag<T default any> :: T -> string
    refers python:caty.core.std.command.builtin.GetTag;

/**
 * 第一の入力値をタグ名とし、第二の入力値をタグ付きにして返す。
 */
command tagged<S default any, T default any> :: [string, S?] -> T
    refers python:caty.core.std.command.builtin.Tagged;

/**
 * 入力値のタグを除去して返す。組み込み型が与えられた場合、その値がそのまま返る。
 * 引数が与えられた場合、タグ名と引数を比較し、異なっていた場合は例外を創出する。
 */
command untagged<S default any, T default univ> [string?] :: S -> T
    refers python:caty.core.std.command.builtin.Untagged;

/**
 * コンソールに入力値を書き出す。
 * --nonl オプションが指定された場合、改行を出力しない。
 */
@[console] command cout {"nonl" : boolean?}:: string -> void
    updates stream
    refers python:caty.core.std.command.builtin.ConsoleOut;

/**
 * 標準入力より1行を読み込み、それを文字列として返す。
 */
@[console] command cin [string? prompt] :: void -> string
    refers python:caty.core.std.command.builtin.ConsoleIn;

/**
 * 現在のアプリケーションのアプリケーション情報を返す。
 */
command app :: void -> AppInfo
    updates stream
    reads env
    refers python:caty.core.std.command.builtin.DisplayApp;

/**
 * すべてのアプリケーションのアプリケーション情報を返す。
 */
command apps :: void -> [AppInfo*]
    reads env
    refers python:caty.core.std.command.builtin.DisplayApps;

/**
 * 現在の作業ディレクトリ名を返す。
 * --long オプションが指定された場合、フルパスでの表示となる。
 */
@[console, deprecated] command home {"long":boolean?} :: void -> string
    reads env
    refers python:caty.core.std.command.builtin.Home;

/**
 * 現在の作業ディレクトリ名を返す。
 */
command location :: void -> string
    reads env
    refers python:caty.core.std.command.builtin.Location;

/**
 * プロジェクト名を返す。
 */
command proj :: void -> string
    reads env
    refers python:caty.core.std.command.builtin.Project;

/**
 * 現在のアプリケーションのマニフェストを返す。
 * これは通常 _manifest.json に書かれている情報である。
 * _manifest.json が存在しない場合、 Caty が自動生成した設定が表示される。
 */
@[console] command manifest :: void -> AppManifest
    reads env
    refers python:caty.core.std.command.builtin.Manifest;

/**
 * ファイルに関連付けられたスクリプトを実行する。
 *
 */
@[console] command exec-context<S default any, T default any> [string] :: S -> T
    uses [pub, include, interpreter]
    refers python:caty.core.std.command.builtin.ExecContext;

/**
 * ファイルに対する関連付けを出力する。
 *
 */
@[console] command assoc  
                       :: void -> Assocs
                       {} [string]         :: void -> Assoc
                       {} [string, string] :: void -> string | null
    refers python:caty.core.std.command.builtin.Assoc;

/**
 * ファイルタイプを出力する。
 *
 *
 */
@[console] command filetype :: void -> FileTypes
                          {} [string] :: void -> FileType | null
        reads pub
        refers python:caty.core.std.command.builtin.ShowFileType;

/**
 * リダイレクト処理。引数のパスに対してそのままリダイレクトする。
 */
command redirect [string] :: void -> never
                 :: string -> never
    breaks Redirect
    reads env
    refers python:caty.core.std.command.builtin.Redirect;

/**
 * スクリプトローカルスキーマの定義。
 * CatyFIT で使うためのコマンドなので、ユーザが明示的に使う事は想定していない。
 */
command define-local-schema :: string -> void
    reads schema
    refers python:caty.core.std.command.builtin.LocalSchema;

/**
 * バイナリデータへの変換。
 * 引数でフォーマットを指定し、入力文字列をそのフォーマットのバイナリと解釈して返す。
 * 特に指定しなかった場合、 base64 と解釈される。
 */
command binary [("base64"|"raw")?] :: string -> binary
    refers python:caty.core.std.command.builtin.Binary;

/**
 * フォーリンデータを出力する。
 */
command foreign :: void -> foreign
    refers python:caty.core.std.command.builtin.Foreign;


/**
 * 環境変数の一覧の出力
 */
command env :: void -> object
    reads env
    refers python:caty.core.std.command.builtin.ListEnv;

/**
 * JSON オブジェクトのプロパティ名のリストを返す。
 */
command properties :: object -> [string*]
    refers python:caty.core.std.command.builtin.Properties;

/** 入力の型を判断する */
command typeof :: any -> BuiltinTypeName 
    refers python:caty.core.std.command.builtin.TypeOf;

/** 入力の型が引数で指定された名前の型であるかどうかを判断する */
command typeis [BuiltinTypeName] :: any -> boolean
refers python:caty.core.std.command.builtin.TypeIs;

/**
 * undefined値を出力する。
 *
 */
command undefined :: void -> undefined
    refers python:caty.core.std.command.builtin.Undef;
    
/** リクエスト情報からスクリプトコードを選択する。
 * method, verb, path からディスパッチされるスクリプトのテキストを
 * stringデータとして出力する。
 * 適切なスクリプトがないときはnullを出力する。
 */
command select-script {
    "method" :  ("GET"|"POST"|"PUT"|"DELETE"|"HEAD")?,
    "verb" : string?,
    "fullpath": boolean?,
    "exception": boolean?,
    "check": boolean?,
    } [string] :: void -> (string | null)
    refers python:caty.core.std.command.builtin.SelectScript;


/** リクエスト情報からアクションを選択する。
 * method, verb, path からディスパッチされるスクリプトのテキストを
 * stringデータとして出力する。
 * 適切なアクションがないときはnullを出力する。
 */
command select-action {
    "method" :  ("GET"|"POST"|"PUT"|"DELETE"|"HEAD")?,
    "verb" : string?,
    "fullpath": boolean?,
    "exception": boolean?,
    "check": boolean?,
    } [string] :: void -> (string | false)
    refers python:caty.core.std.command.builtin.SelectAction;

type _trace = [(string|null|boolean)*](minItems=1);

/** リクエストに対してマッチしたリソースクラス名を試行した順番に出力する */
command trace-dispatch
{
  @[default("GET")]
  "method" : ("GET"|"POST"|"PUT"|"DELETE"|"HEAD")?,
  @[default(false)]
  "fullpath": boolean?,
  "verb"   : string?,
  "check": boolean?,
} [string path]
:: void -> @EXISTS _trace | @FAILED _trace
    refers python:caty.core.std.command.builtin.TraceDispatch;

type HelpInfo = deferred @* object;

/**
* モジュール/コマンド/型のヘルプを表示する。
* 型のヘルプを出力する時は--typeオプションを、コマンドのヘルプを出力する時は--commandオプションをつける。
* そのどちらも付けられなかった場合、このヘルプが表示される。
* 引数のフォーマットは以下の通り。
* 
* {{{
*     *               ビルトインモジュールのコマンド一覧を表示
*     command         ビルトインモジュールの command のヘルプを表示
*     *:              モジュール一覧を表示
*     module:*        module のコマンド一覧を表示
*     module:command  module:command のヘルプを表示
* }}}
* 
* これはコマンドのヘルプのフォーマットであるが、型のヘルプも同様である。
* オプションの--jsonが指定された場合、JSON形式のヘルプが返る(未実装)。
*
* == コマンド特有のオプション
*
* --filterオプションはコマンド一覧を出力する際、
* 出力するコマンドをfilterに限定するために用いる。
*
* == 型特有のオプション
*
* --exceptionオプションは型一覧を出力する際、
* 出力する型を例外型に限定するために用いる。
*
* == コンソールでのみ有効な特殊コマンド
* 
* change APP_NAME  : アプリケーションをAPP_NAMEに変更する。短縮コマンドはch, cd
* quit             : Catyシェルを終了する。
* reload           : グローバル設定とアプリケーションの再読み込み。短縮コマンドはl
* server start PORT: PORTでCatyサーバを稼働させる。
*        stop      : Catyサーバを停止する。
*/
command help
{
  @[default(false), without(["type", "resource"])]
  "command" : boolean?,

  @[default(false), without(["command", "resource"])]
  "type" : boolean?,

  @[default(false), without(["command", "type"])]
  "resource" : boolean?,

  // 以下は、既存のhelp, typeのオプション
  
  @[default(false), not-implemented]
  "json": boolean?,

  @[default(false), with("command")]
  "filter": boolean?,

  @[default(false), with("type")]
  "exception": boolean?,

} [string? pattern] :: void -> (string | HelpInfo)
  reads [interpreter, schema]
  refers python:caty.core.std.command.builtin.Help;

command hc {

  @[default(false)]
  "filter": boolean?,

} [string? pattern] :: void -> void {
  help --command %--filter %1 | cout
};

command ht {

  @[default(false)]
  "exception": boolean?,

} [string? pattern] :: void -> void {
  help --type %--exception %1 | cout
};

command hr {
} [string? pattern] :: void -> void {
  help --resource %1 | cout
};

command h :: void -> void {
    help | cout
};

/** 例外データを作る。
 * tagが既存の例外型に対応してないときは、ExceptionNotFound例外。
 */
command make-exception [string tag, string message] :: void -> Exception
    throws ExceptionNotFound
    reads schema
    refers python:caty.core.std.command.builtin.MakeException;


/** 例外を投げる。
 * 次のときは何もしないで pass として振舞う
 * # 入力が例外（Exception）型でなかったとき
 * # 入力が構造的に例外型だが、定義されてないとき
 */
command throw-if-can :: any? -> any?
    throws Exception
    reads schema
    refers python:caty.core.std.command.builtin.Throw;

/**
 * [文字列, データ]のペアの配列からオブジェクトを作る。
 * 上記のペアの第一要素がオブジェクトのプロパティとなる。
 */
command array-to-object :: [[string, any]*] -> object
    refers python:caty.core.std.command.builtin.ArrayToObject;

/**
 * オブジェクトから[文字列, データ]のペアの配列を作る。
 */
command object-to-array :: object -> [[string, any]*]
    refers python:caty.core.std.command.builtin.ObjectToArray;

/** 
 * 引数のコマンドあるいはCatyScriptを呼び出す。
 */
command call<S default any, T default any> [string command_name] :: S -> T
    reads [pub, scripts, interpreter]
    refers python:caty.core.script.interpreter.CallCommand;

/** 
 * 引数のコマンドあるいはCatyScriptを呼び出し、制御をそちらに移す。
 */
command forward<S default any, T default any>  [string command_name] :: S -> never
    signals T
    reads [pub, scripts, interpreter]
    refers python:caty.core.script.interpreter.Forward;

/**
 * 引数で指定されたミリ秒だけ停止する。
 * 引数が省略された場合は1秒(1000ミリ秒)停止する。
 */
command sleep<T default any> [integer(minimum=0)? millisec] :: T -> T
    refers python:caty.core.std.command.builtin.Sleep;
   
/**
 * 入力データを文字列化する。
 */
command to-string :: any -> string
    refers python:caty.core.std.command.builtin.ToString;
   

"""
