#coding: utf-8
from __future__ import with_statement
from caty.core.command import Builtin
from caty.command import MafsMixin
from caty.jsontools import tagged
name = 'file'
schema = ''

class FileUtilMixin(MafsMixin):
    def setup(self, path):
        self.path = path

    def open(self, mode='rb'):
        return MafsMixin.open(self, self.path, mode)
    
    def opendir(self):
        return MafsMixin.opendir(self, self.path)

class ZeroFile(FileUtilMixin, Builtin):
    command_decl = u"""
        /**
         * 引数で指定したファイル名で空のファイルを作成する。
         */
        command zerofile [string] :: void -> @OK string
            uses [data, include, pub]
            refers python:caty.command.file.ZeroFile;
    """

    def execute(self):
        fo = self.open("rb") 
        # wモードだと即座に作られる、既存ファイルは書き込むまで切りつめされない
        if (fo.exists):
            fo.close()
            r = tagged(u'OK', fo.path)
        else:
            fo.close()
            fo = self.open("wb") # これだけで作られる。
            fo.close()
            r = tagged(u'OK', fo.path)
        return r

class Exists(FileUtilMixin, Builtin):
    command_decl = u"""
        /**
         * 引数で指定したファイルが存在するかどうかを返す。
         */
        command exists {"pred": boolean} [string] :: void -> @OK string | @NG string | boolean
            uses [data, include, pub]
            refers python:caty.command.file.Exists;
    """
    def setup(self, opts, path):
        self.__pred = opts.pred
        FileUtilMixin.setup(self, path)
    
    def execute(self):
        fo = self.open()
        r = fo.exists
        fo.close()
        if self.__pred:
            return r
        if r:
            return tagged(u'OK', self.path)
        else:
            return tagged(u'NG', self.path)

class ReadFile(FileUtilMixin, Builtin):
    command_decl = u"""
    /**
     * 引数で指定したファイルを読み込み、その値を返す。ファイルがバイナリファイルの場合の動作は保証しない。
     */
    command read [string] :: void -> string | binary
        reads [data, include, pub, behaviors, scripts]
        refers python:caty.command.file.ReadFile;
    """

    def execute(self):
        return self.open().read()
        
class ReadFileI(FileUtilMixin, Builtin):
    command_decl = u"""
    /**
     * 入力で指定したファイルを読み込み、その値を返す。ファイルがバイナリファイルの場合の動作は保証しない。
     */
    command read-i [] :: string -> string | binary
        reads [data, include, pub, behaviors, scripts]
        refers python:caty.command.file.ReadFileI;
    """
    def setup(self, opts):
        self.dir = opts.dir

    def execute(self, input):
        self.path = input
        return self.open().read()

class WriteFile(FileUtilMixin, Builtin):
    command_decl = u"""
    /**
     * 引数で指定したファイルに入力値を書き込む。
     */
    command write [string] :: string -> void
        updates [data, include, pub]
        refers python:caty.command.file.WriteFile;
    """

    def execute(self, input):
        with self.open('wb') as f:
            f.write(input)

class DeleteFile(FileUtilMixin, Builtin):
    command_decl = u"""
    /**
     * 引数で指定したファイルまたはディレクトリを削除する。
     */
    command delete [string] :: void -> null
        updates [data, include, pub]
        refers python:caty.command.file.DeleteFile;
    """

    def execute(self):
        p, m = self.parse_canonical_path(self.path)
        if m.is_dir(p):
            d = self.opendir()
            d.delete(True)
        else:
            f = self.open('wb')
            f.delete()


class LastModified(FileUtilMixin, Builtin):
    command_decl = u"""
    /**
     * 引数で指定したファイルの最終更新時刻を取得する。
     */
    command lastmodified [string] :: void -> string
        reads [data, include, pub, behaviors, scripts]
        refers python:caty.command.file.LastModified;
    """
   

    def execute(self):
        return unicode(self.open().last_modified)

class RealPath(FileUtilMixin, Builtin):

    command_decl = u"""
    /**
     * 引数で指定したファイルの実際のファイルシステム上の絶対パスを返す。
     * mafs のバックエンドが実際のファイルシステムでない場合、引数がそのまま返される。
     */
    command realpath [string] :: void -> string
        reads [data, include, pub, behaviors, scripts]
        refers python:caty.command.file.RealPath;
    """

    def execute(self):
        return unicode(self.open().real_path)

class MakeDir(FileUtilMixin, Builtin):
    command_decl = u"""
    /**
     * ディレクトリを作成する。
     */
    command mkdir [string] :: void -> void
        updates [pub, include, data, behaviors, scripts]
        refers python:caty.command.file.MakeDir;
    """
    def execute(self):
        self.opendir().create()


