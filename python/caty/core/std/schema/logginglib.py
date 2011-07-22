#coding: utf-8
name = u'logging'
schema =u"""
/**
 * app.logにデバッグログを書き込む。
 * --coutオプションが指定された場合、標準出力にもログを書き出す。
 */
command debug {"cout": boolean?} :: string -> void
    uses [stream, logger]
    refers python:caty.core.std.command.logginglib.Debug;

/**
 * app.logにインフォメーションログを書き込む。
 * --coutオプションが指定された場合、標準出力にもログを書き出す。
 */
command info {"cout": boolean?} :: string -> void
    uses [stream, logger]
    refers python:caty.core.std.command.logginglib.Info;

/**
 * app.logに警告ログを書き込む。
 * --coutオプションが指定された場合、標準出力にもログを書き出す。
 */
command warning {"cout": boolean?} :: string -> void
    uses [stream, logger]
    refers python:caty.core.std.command.logginglib.Warning;

/**
 * app.logにエラーログを書き込む。
 * --coutオプションが指定された場合、標準出力にもログを書き出す。
 */
command error {"cout": boolean?} :: string -> void
    uses [stream, logger]
    refers python:caty.core.std.command.logginglib.Error;


"""


