#coding: utf-8

name = u'authutil'
schema = u"""
type TokenProperty = {
    "$_catySecureToken": string,
};

type TokenEmbeded = any;

type TokenCheckResult<T> = @OK T | @NG null;

type Token = string;

type TokenSet = [Token*];

type TargetForm = string | Response;



/**
 * トークンの自動埋め込み。
 * HTML フォームにトークンを埋め込む。
 * 主に以下のように print コマンドにつなげる形で実行する。
 *
 * {{{
 * print /form.html | authutil:embed-token
 * }}}
 */
command embed-token :: TargetForm -> TargetForm
    uses [session, token]
    refers python:caty.core.std.command.authutil.EmbedToken;

/**
 * リクエストトークンの生成。
 */
command gen-token :: void -> string
    uses [session, token]
    refers python:caty.core.std.command.authutil.GenerateToken;

/**
 * セキュリティトークンチェック。
 *
 * 入力に含まれるトークンとサーバ側のトークンを照合し、入力のトークンがサーバ側に含まれていなければエラーとする。
 *
 */
command check-token<T> :: TokenEmbeded -> TokenCheckResult<T>
    reads token
    uses session
    refers python:caty.core.std.command.authutil.CheckToken;
"""

