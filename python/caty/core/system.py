#coding: utf-8
import caty
from caty.core.application import *
from caty.core.applicationgroup import *
from caty.util.path import join
from caty.core.script import node
from caty.core.std.schema import (builtin, 
                                  authutil,
                                  debug, 
                                  file, 
                                  filtercmd, 
                                  jsonlib, 
                                  listlib, 
                                  logginglib,
                                  strg, 
                                  test, 
                                  text, 
                                  user, 
                                  fit, 
                                  gen,
                                  oslib,
                                  path, 
                                  xjsonlib, 
                                  setlib, 
                                  viva,
                                  http)

from pbc import PbcObject, Contract

class System(PbcObject):
    u"""Caty のコアシステム。
    システム起動時に初期化され、内部に全ての Caty アプリケーションを包含する。
    System オブジェクトは一つの Caty プロセスについて一つだけ作成されるものとする。
    """
    __properties__ = ['app_names']

    @brutal_error_printer
    def __init__(self, encoding=None, is_debug=True, quiet=False, no_ambient=False, no_app=False):
        caty.core.runtimeobject.i18n = I18nMessage({}, writer=cout, lang='en') # フォールバック
        if quiet:
            class NullWriter(object):
                def write(self, *args):
                    pass
            self.__cout = NullWriter()
        else:
            self.__cout = cout
        if not encoding:
            encoding = locale.getpreferredencoding()
        self._init_temp()
        self._init_logger()
        gcfg = xjson.load(open('_global.xjson'))
        self._global_config = GlobalConfig(gcfg, 
                                           self._validate_encoding(encoding))
        self._global_app = None
        messages = self._load_system_messages()
        self.i18n = I18nMessage(messages, writer=cout, lang=self._global_config.language)
        caty.core.runtimeobject.i18n = self.i18n # 改めて設定
        self.i18n.write('Loading system data')
        self._casm = casm.initialize(self,
                                     [builtin, node],
                                     [
                                     authutil,
                                     debug, 
                                     file, 
                                     filtercmd, 
                                     jsonlib, 
                                     listlib, 
                                     logginglib,
                                     strg, 
                                     test, 
                                     text, 
                                     user, 
                                     fit, 
                                     gen,
                                     oslib, 
                                     xjsonlib, 
                                     path,
                                     viva,
                                     http])

        gag = ApplicationGroup('', self._global_config, no_ambient, no_app, self)
        self._global_app = gag._apps[0]
        self._global_app.finish_setup()
        self._casm.set_global(self._global_app)
        #self._casm._core.schema_finder("GlobalConfig").validate(gcfg)
        # アプリケーショングループの順序は rc.caty の実行順序に関わる
        # common, main, extra, examples という順序は固定
        self._app_groups = [
            ag for ag in [
                ApplicationGroup('common', self._global_config, no_ambient, no_app, self),
                ApplicationGroup(USER, self._global_config, no_ambient, no_app, self),
                ApplicationGroup('extra', self._global_config, no_ambient, no_app, self),
                ApplicationGroup('examples', self._global_config, no_ambient, no_app, self),
                ApplicationGroup('develop', self._global_config, no_ambient, no_app, self),
            ] if ag.exists
        ]
        self._apps = reduce(operator.add, map(ApplicationGroup.apps.fget, self._app_groups))
        self.__app_names = [app.name for app in self._apps]
        self._app_map = {}
        if is_debug:
            caty.DEBUG = True
        self.__debug = is_debug
        for app in self._apps:
            if app.name in self._app_map:
                raise Exception(self.i18n.get('Application name conflicted', name=app.name))
            self._app_map[app.name] = app
        for app in self._app_map.values():
            app.finish_setup()
        self._app_map['global'] = self._global_app
        self.__app_names.append(u'global')
        self._apps.append(self._global_app)
        #for app in self._app_map.values():
        #    app.finish_setup()
        for group in self._app_groups:
            group.exec_rc_script()
        self.__cout = cout
        PbcObject.__init__(self)

    def get_app(self, app_name):
        app = self._app_map[app_name]
        return app

    def _load_system_messages(self):
        from glob import glob
        base = xjson.loads(open('messages/default.xjson').read())
        msg = {}
        for m in base:
            msg[m] = {}
        for path in glob('messages/[a-z][a-z].xjson'):
            messages = xjson.loads(unicode(open(path).read(), 'utf-8'))
            lang = path.split(os.path.sep)[1].split('.')[0]
            for e_msg, trans in messages.items():
                if e_msg not in msg:
                    msg[e_msg] = {lang: trans}
                else:
                    msg[e_msg][lang] = trans
                    
        return msg

    def _init_logger(self):
        import caty.util.syslog as syslog
        self._access_logger = syslog.get_access_log()
        self._error_logger = syslog.get_error_log()
        self._start_logger = syslog.get_start_log()
    
    @property
    def access_logger(self):
        return self._access_logger

    @property
    def error_logger(self):
        return self._error_logger

    @property
    def casm(self):
        return self._casm

    @property
    def app_names(self):
        return self.__app_names

    @property
    def server_module_name(self):
        return self._global_config.server_module_name

    @property
    def sysencoding(self):
        return self._global_config.sysencoding

    @property
    def dummy_app(self):
        return DummyApplication(self)

    @property
    def addrsDenied(self):
        return self._global_config._addrsDenied

    @property
    def addrsAllowed(self):
        return self._global_config._addrsAllowed


    @property
    def enable_script_cache(self):
        return self._global_config.enableScriptCache
    
    @property
    def enable_http_method_tunneling(self):
        return self._global_config.enableHTTPMethodTunneling

    @property
    def appencoding(self):
        return self._global_config.encoding

    def _validate_encoding(self, encoding):
        try:
            codecs.lookup(encoding)
            return encoding
        except LookupError:
            debug.write('Waring: Unknown encdoing %s. Set ascii to system encoding' % self.encdoing)
            return 'ascii'

    @property
    def cout(self):
        return self.__cout

    @property
    def ignore_names(self):
        return self._global_config.ignoreNames

    @property
    def useMultiprocessing(self):
        return self._global_config._useMultiprocessing
    
    @property
    def project_name(self):
        return self._global_config._project_name

    @property
    def debug(self):
        return self.__debug
    
    def reload_library(self):
        files = list(self._find_packages())
        for f in files:
            try:
                exec 'import %s' % f
                exec 'reload(%s)' % f
            except:
                import traceback
                traceback.print_exc()
                self.i18n.write('Failed to reload $name', name=f)

    def reload_global(self):
        self._casm.set_global(None)
        self._global_app.reload()
        self._casm.set_global(self._global_app)

    def _find_packages(self):
        for r, d, f in os.walk('./lib/'):
            for p in f:
                e = (r + '/' + p).replace('//', '/').replace('./lib/', '')
                if e.endswith('.py'):
                    yield e.replace('.py', '').replace('/__init__', '').replace('/', '.')

    def _init_temp(self):
        # tempfileで使うディレクトリの作成とtempfileモジュールの初期化
        if not os.path.exists('./_tmp'):
            os.mkdir('./_tmp')
        tempfile.tempdir = os.path.join(os.getcwd(), '_tmp')
        # 以前のプロセスが使ったテンポラリファイルの削除
        for root, dirs, files in os.walk(tempfile.gettempdir(), topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))

    def __invariant__(self):
        assert len(self._app_groups) > 0
        assert len(self._apps) > 0
        assert ROOT in self._app_map

    if caty.DEBUG:
        def _contains_name(self, name):
            assert name in self._app_map

        get_app = Contract(get_app)
        get_app.require += _contains_name


    def debug_on(self):
        caty.DEBUG = True
        self.__debug = True

    def debug_off(self):
        caty.DEBUG = False
        self.__debug = False

    def to_name_tree(self):
        apps = {
            'kind': 'ns:apps',
            'childNodes': {},
        }
        for k, v in self._app_map.items():
            apps['childNodes'][k] = v.to_name_tree()
        return {
            'kind': u'c:sys',
            'childNodes': {
                u'': apps
            }
        }

