#coding: utf-8

name='http'
schema = u"""
/**
 * 与えられたパスに対しての302 Foundレスポンスを出力する。
 */
command found [string] :: void -> Redirect
    refers python:caty.core.std.command.http.Found;

/**
 * 与えられたパスに対しての403 Forbiddenを出力する。
 */
command forbidden [string] :: void -> never
    refers python:caty.core.std.command.http.Forbidden;

/**
 * 与えられたパスに対しての404 Forbiddenを出力する。
 */
command not-found [string] :: void -> never
    refers python:caty.core.std.command.http.NotFound;

/**
 * 与えられたパスに対しての400 Bad Requestを出力する。
 */
command bad-request [string path, string method] :: void -> never
    refers python:caty.core.std.command.http.BadRequest;

/**
 * 与えられたパスに対しての405 Method Not Allowedを出力する。
 */
command not-allowed [string path, string method] :: void -> never
    refers python:caty.core.std.command.http.NotAllowed;
"""
