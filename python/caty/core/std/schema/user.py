#coding: utf-8

name = 'user'
schema = u"""
type UserInfo = {
    "userid": string,    // ID。この値は一意でなければならない。
    "username": string?, // 名前。必須ではない
    "role": [string(minLength=1)*]?, // 必要ないなら使わなくてよい
    *: any, // 他のオプショナルな項目は何でも良い
};

type RegistryInfo = UserInfo & {
    "password": string,
    *: any
};

/**
 * ユーザーが存在するかどうかを返す。
 */
command exists :: string -> boolean
    reads storage
    refers python:caty.core.std.command.user.ExistsUser;

/**
 * 新規ユーザの登録を行う。
 */
command add :: RegistryInfo -> boolean
               uses storage
               refers python:caty.core.std.command.user.AddUser;

/**
 * ユーザの削除を行う。入力値はユーザのアカウント名である。
 */
command delete :: string -> boolean
        uses storage
        refers python:caty.core.std.command.user.DelUser;

/**
 * パスワードの変更を行う。
 */
command password :: RegistryInfo -> boolean
    uses storage
    refers python:caty.core.std.command.user.ChangePassword;

/**
 * ユーザ情報の取得を行う。
 **/
command info :: void -> UserInfo
    reads user
    refers python:caty.core.std.command.user.GetUserInfo;
    
/**
 * ユーザ情報を最新の情報に更新する。
 */
command update-info :: void -> void
    reads storage
    uses user
    refers python:caty.core.std.command.user.UpdateInfo;


type LoginForm = {
    "userid": string, 
    "password": string, 
    "succ": string?,
};


/**
 * ログイン処理を行う。
 * 入力値のうちuseridとpasswordは必須である。
 * succはログイン成功/失敗時に遷移する先のパスである(省略時は/へ)。
 * ログイン成功/失敗はタグで区別され、成功時は遷移先のパスが、
 * 失敗時はエラーメッセージがタグ付けされる。
 */
command login :: LoginForm -> @OK string | @NG string
                reads [storage, env]
                uses [user, session]
                refers python:caty.core.std.command.user.Login;

/**
 * ログインしているか否かのチェックを行う。
 * ログインしていれば @OK タグを付けた上で入力をコピーして返す。
 * 未ログインの場合は @NG タグを付けた上で入力をコピーして返す。
 * --userid オプションでユーザアカウントを指定することもでき、その場合はアカウント名の照合も行う。
 *
 */
command loggedin<T> {"userid":string?} :: T -> @OK T | @NG T
                                reads user
                                refers python:caty.core.std.command.user.Loggedin;


/**
 * ログアウト処理。
 * セッション情報を破棄し、入力されたパスへ遷移する。
 * 未ログイン時でも同じく遷移する。
 */
command logout :: string -> Redirect
    uses [user, session]
    refers python:caty.core.std.command.user.Logout;

"""

