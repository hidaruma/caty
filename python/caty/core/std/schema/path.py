#coding:utf-8
name = u'path'
schema = u"""

type ext  = deferred string;

/** Pythonの os.path.join と同じでよかんべ */
command join :: [path*] -> path
    refers python:caty.core.std.command.path.Join;

/** Pythonの os.path.split と同じでよかんべ */
command split :: path -> [path head, path tail]
    refers python:caty.core.std.command.path.Split;

/** ディレクトリ部 */
command dir :: path -> path
    refers python:caty.core.std.command.path.Dir;

/** ベース名 */
command base :: path -> path
    refers python:caty.core.std.command.path.Base;

/** 拡張子 */
command ext :: path -> ext
    refers python:caty.core.std.command.path.Ext;

/** ディレクトリと拡張子を除いた部分 */
command trunk :: path -> path
    refers python:caty.core.std.command.path.Trunk;

/** 拡張子だけ取り替える */
command replace-ext :: [path, ext] -> path
    refers python:caty.core.std.command.path.ReplaceExt;


type path = string(format="file-pattern");
type file-pattern = string(format="file-pattern");

/** ファイル名がパターンにマッチするかどうかを返す */
command matches 
  {
    @[default(false)]
    "boolean": boolean?
  }
  [string] 
  :: string -> (@True string | @False string) | boolean
  refers python:caty.core.std.command.path.Matches;
"""
