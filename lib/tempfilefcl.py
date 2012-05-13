# -*- coding: utf-8 -*- 
#
# これはtempfileファシリティの実装クラス
# lib/ ディレクトリに置く。
#
# トランザクションサポートのコールバックはサボっている。
# （必要性も薄いと思われる。）
# 
from __future__ import with_statement
import os
import tempfile

class TempFile(object):
    initialized = False
    the_instance = None
    temp_dir_name = "caty_tmp"

    @classmethod
    def _initialize(cls, config):
        if cls.initialized:
            return None
        if config is None:
            config = {}
        dir_name = config.get(u"catyDirName", "caty_tmp") + str(os.getpid())
        cls.temp_dir_name = os.path.join(tempfile.gettempdir(), dir_name)
        if not os.path.exists(cls.temp_dir_name):
            os.mkdir(cls.temp_dir_name)
        if not os.path.isdir(cls.temp_dir_name):
            return u"%s exists, but not a directory" % cls.temp_dir_name
        else:
            cls.initialized = True
            return None

    @classmethod
    def _finalize(cls):
        if not cls.initialized:
            return
        dir = TempFile.temp_dir_name
        files = os.listdir(TempFile.temp_dir_name)
        for f in files:
            os.remove(os.path.join(dir, f))
        os.rmdir(dir)
        cls.initialized = False

    @classmethod
    def _create(cls, mode_param):
        mode, param = mode_param
        if not mode == 'use':
            raise Exception(u"bad mode")
        if cls.the_instance is None:
            cls.the_instance = TempFile()
        return cls.the_instance


    def __init__(self):
        pass
        

    def os_dir_path(self):
        return unicode(TempFile.temp_dir_name)

    def os_path(self, name):
        return unicode(os.path.join(TempFile.temp_dir_name, name))

    def list(self):
        return map(lambda f: unicode(f), os.listdir(TempFile.temp_dir_name))

    def read(self, name):
        fname = os.path.join(TempFile.temp_dir_name, name)
        with open(fname, "r") as file:
            return file.read()

    def write(self, data, name):
        fname = os.path.join(TempFile.temp_dir_name, name)
        if isinstance(data, unicode):
            data = data.encode('utf-8') # 決め打ち
        with open(fname, "w") as file:
            file.write(data)
        
    def remove(self, name):
        fname = os.path.join(TempFile.temp_dir_name, name)
        os.remove(fname)


    def _sync(self):
        pass
    def _close(self):
        pass
    def _begin(self):
        pass
    def _commit(self):
        pass
    def _cancel(self):
        pass

