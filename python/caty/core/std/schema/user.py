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
    """
