#coding: utf-8

name = u'secure'
schema = u"""
type TokenProperty = {
    "$_catySecureToken": string,
};

type TokenEmbeded = any;

type TokenCheckResult<T> = @OK T | @NG null;

type Token = string;

type TokenSet = [Token*];

type TargetForm = string | Response;

type LoginForm = {
    "userid": string, 
    "password": string, 
    "succ": string?,
    "fail": string?
};


/**
 * ログイン処理を行う。
 * 入力値のうち userid と password は必須である。
 * succ, fail はそれぞれログイン成功/失敗時に遷移する先のパスである。
 * ただし、 succ, error の仕様は変更される可能性が高い。
 */
command login :: LoginForm -> Redirect
                reads [storage, env]
                uses [user, session]
                refers python:caty.core.std.command.secure.Login;

/**
 * ログインしているか否かのチェックを行う。
 * ログインしていれば @OK タグを付けた上で入力をコピーして返す。
 * 未ログインの場合は @NG タグを付けた上で入力をコピーして返す。
 * --userid オプションでユーザアカウントを指定することもでき、その場合はアカウント名の照合も行う。
 *
 */
command loggedin<T> {"userid":string?} :: T -> @OK T | @NG T
                                reads user
                                refers python:caty.core.std.command.secure.Loggedin;

/**
 * ログアウト処理。
 * セッション情報を破棄し、入力されたパスへ遷移する。
 * 未ログイン時でも同じく遷移する。
 */
command logout :: string -> Redirect
    uses [user, session]
    refers python:caty.core.std.command.secure.Logout;

/**
 * トークンの自動埋め込み。
 * HTML フォームにトークンを埋め込む。
 * 主に以下のように print コマンドにつなげる形で実行する。
 *
 * {{{
 * print /form.html | secure:embed-token
 * }}}
 */
command embed-token :: TargetForm -> TargetForm
    uses [session, token]
    refers python:caty.core.std.command.secure.EmbedToken;

/**
 * リクエストトークンの生成。
 */
command gen-token :: void -> string
    uses [session, token]
    refers python:caty.core.std.command.secure.GenerateToken;

/**
 * セキュリティトークンチェック。
 *
 * 入力に含まれるトークンとサーバ側のトークンを照合し、入力のトークンがサーバ側に含まれていなければエラーとする。
 *
 */
command check-token<T> :: TokenEmbeded -> TokenCheckResult<T>
    reads token
    uses session
    refers python:caty.core.std.command.secure.CheckToken;
"""
