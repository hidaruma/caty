#coding: utf-8
from caty import mafs, session
from caty.util.path import join

from copy import deepcopy
import locale
import os

class GlobalConfig(object):
    u"""Caty システムのサイト固有でない情報。
    mafs バックエンド、JSON ストレージ、セッションなどを指定する。
    
    "mafs": string,
    "session": {
        *: any
    }
    """
    def __init__(self, obj, encoding):
        self._raw_data = obj
        fs = obj['mafsModule']
        self._mafs_module = fs
        session_conf = obj.get('session', {'type':'memory', 'expire': 3600})
        secret_key = obj['secretKey']
        self._session_storage = session.initialize({'session': session_conf, 'key': secret_key})
        self._filetypes = mafs.metadata.default_types
        self._encoding = obj.get('encoding', u'utf-8')
        self.server_port = 80
        self.server_name = u''
        self._orig_hosturl = obj['hostUrl']
        self._configure_server()
        self._server_module_name = obj['serverModule']
        self._storage_conf = obj.get('storage', {'type': 'sqlite', 'path': './storage.db'})
        self._sysencoding = unicode(encoding or locale.getpreferredencoding())
        self._mime_types = {}
        self._project_name = obj.get('projectName', unicode(os.path.basename(os.getcwd()), self._encoding))
        self._associations = {
        }
        self._addrsAllowed = obj.get('addrsAllowed', None)
        self._addrsDenied = obj.get('addrsDenied', [])
        self._ignoreNames = obj.get('ignoreNames', ['CVS'])
        self._language = obj.get('language', 'en')
        for k, v in self._filetypes.items():
            assoc = v.get('assoc', None)
            if assoc:
                self._associations[k] = assoc
            it = v.get('isText', True)
            ct = v.get('contentType', u'text/plain' if it else u'application/octet-stream')
            ds = v.get('description', u'')
            t = {
                'isText': it,
                'contentType': ct,
                'description': ds,
            }
            self._mime_types[k] = t
        if 'vcsModule' in obj:
            exec 'import %s as caty_vcs_module' % obj['vcsModule']
            self._vcs_module = caty_vcs_module
        else:
            self._vcs_module = None

        self._enableScriptCache = obj.get('enableScriptCache', False)
        self._enableHTTPMethodTunneling = obj.get('enableHTTPMethodTunneling', False)
        self._useMultiprocessing = obj.get('useMultiprocessing', True)

    def mafs_initializer(self, app, system, type):
        initializer = MafsInitializer(self._mafs_module, app, system, type)
        initializer.encoding = self.encoding
        return initializer
        #return (lambda root, target, mime_types, encoding=self.encoding: 
        #                  initializer(root, target, mime_types, encoding))

    def _configure_server(self):
        import urllib
        host, port = urllib.splitport(self._orig_hosturl)
        if port is None:
            self.server_name = self._orig_hosturl
        else:
            self.server_name = host
            self.server_port = int(port)

    @property
    def session_storage(self):
        return self._session_storage

    @property
    def host_url(self):
        if self.server_port == 80:
            return self.server_name
        else:
            return self.server_name + ':' + str(self.server_port)

    @property
    def encoding(self):
        return self._encoding

    @property
    def sysencoding(self):
        return self._sysencoding

    @property
    def server_module_name(self):
        return self._server_module_name

    @property
    def storage_conf(self):
        return self._storage_conf

    @property
    def filetypes(self):
        return self._filetypes

    @property
    def mime_types(self):
        return deepcopy(self._mime_types)

    @property
    def associations(self):
        return deepcopy(self._associations)

    @property
    def vcs_module(self):
        return self._vcs_module

    @property
    def addrsDenied(self):
        return self._addrsDenied

    @property
    def addrsAllowed(self):
        return self._addrsAllowed

    @property
    def enableScriptCache(self):
        return self._enableScriptCache

    @property
    def enableHTTPMethodTunneling(self):
        return self._enableHTTPMethodTunneling

    @property
    def ignoreNames(self):
        return self._ignoreNames

    @property
    def language(self):
        return self._language

    @ property
    def project_name(self):
        return self._project_name

class MafsInitializer(object):
    u"""mafs 初期化オブジェクト。
    mafs は数あるファシリティの中でももっとも込み入った初期化手順となっている。
    そのため、 MafsInitializer でラッピングして処理の簡略化を図っている。
    """
    def __init__(self, type, app=None, system=None, res_type=None):
        u"""MafsInitializer は最低一つの引数で初期化される。
        type は必須の引数であり、 mafs 実装モジュールの名称を文字列で渡す。
        app は mafs に紐付けられるアプリケーション、 system はそのアプリケーションの属するシステムである。
        res_type は pub, include, schemata など、アプリケーションディレクトリ直下のディレクトリ名か、
        特殊な用途に用いる root のいずれかである。
        """

        exec 'import %s as mafs_impl' % type
        self.mafs_impl = mafs_impl
        self.app = app
        self.system = system
        self.res_type = res_type
        self.encoding = u'utf-8'

    def init(self, root, target, mime_types, encoding=None):
        u"""初期化処理。新たな初期化済み mafs ファシリティを返す。

        root は初期化対象の mafs の論理的なルートディレクトリであり、 target はその直下の任意のディレクトリである。
        通常のファイルシステムをバックエンドに用いた場合、これは chroot のように働く。
        それに対して RDBMS 上に mafs を構築した場合などは、バックエンドの実装によっては動作が異なる。
        ただし、例えば /main/app/pub というディレクトリツリーが mafs 上にある場合、
        / を root にし、また main を target にした場合は /main をルートとしてファイルアクセスが可能にならなければならない。

        mime_types は拡張子ごとの MIME タイプ情報である。

        encoding はエンコーディング情報である。
        """
        if target is None:return
        return mafs.initialize(self.app,
                               self.system,
                               self.res_type,
                               fs=self.mafs_impl, 
                               root_dir=join(root, target), 
                               mime_types=mime_types, 
                               encoding=encoding if encoding else self.encoding)

    def __call__(self, *args, **kwds):
        return self.init(*args, **kwds)

    @property
    def name(self):
        return self._group_name

    @property
    def apps(self):
        return self.apps

    @property
    def global_config(self):
        return self._global_config


