#coding: utf-8
import caty
from caty.core.application import *
from caty.core.applicationgroup import *
from caty.jsontools.util import ManifestReader, FileOpener
from caty.jsontools import xjson, prettyprint
from caty.util.path import join
from caty.core.script import node
from customimporter import make_custom_import

from glob import glob

class System(object):
    u"""Caty のコアシステム。
    システム起動時に初期化され、内部に全ての Caty アプリケーションを包含する。
    System オブジェクトは一つの Caty プロセスについて一つだけ作成されるものとする。
    """

    @brutal_error_printer
    def __init__(self, options):
        encoding = options.system_encoding
        is_debug = options.debug
        quiet = options.quiet
        no_ambient = options.no_ambient
        no_app = options.no_app
        app_names = options.apps or [u'root']
        force_app = options.force_app
        wildcat = options.unleash_wildcats
        prj_manifest = options.prj_manifest
        make_custom_import()
        caty.core.runtimeobject.i18n = I18nMessage({}, writer=cout, lang='en') # フォールバック
        self.force_app = force_app
        self.no_ambient = no_ambient
        self.wildcat = wildcat
        self.hcon_port = None
        self.uuserver_port = None
        self.hcon_name = None
        self.public_commands = None
        if quiet:
            class NullWriter(object):
                def write(self, *args):
                    pass
                def writeln(self, *args):
                    pass
            self.__cout = NullWriter()
        else:
            self.__cout = cout
        if not encoding:
            encoding = locale.getpreferredencoding()
        self._init_temp()
        self._init_logger()
        if prj_manifest:
            prjfile = ('prj-manifest.' + prj_manifest+'.xjson')
        else:
            prjfile = 'prj-manifest.xjson'
        gcfg = None
        if os.path.exists(prjfile):
            gcfg = ManifestReader(FileOpener(os.getcwd()), prjfile).read()
        if not gcfg:
            import random
            import string
            gcfg = {
                "serverModule": u"caty.front.web.simple",
                "language": u"ja",
                "enableScriptCache": False,
                "projectName": unicode(os.path.basename(os.getcwd())),
                "encoding": u"utf-8",
                "hostUrl": u"http://localhost:8000",
                "useMultiprocessing": False,
                "secretKey": u''.join([random.choice(string.ascii_letters+string.digits) for c in range(29)]),
                "enableHTTPMethodTunneling": True,
                "session": {
                    "module": u"caty.session.memory",
                    "conf": {
                        "expire": 3600,
                    }
                },
                "mafsModule": u"caty.mafs.stdfs"
            }
            open('prj-manifest.xjson', 'wb').write(xjson.dumps(gcfg))
        self._global_config = GlobalConfig(gcfg, 
                                           self._validate_encoding(encoding))
        self._global_app = None
        messages = self._load_system_messages()
        self.i18n = I18nMessage(messages, writer=cout, lang=self._global_config.language)
        caty.core.runtimeobject.i18n = self.i18n # 改めて設定
        # catyアプリケーション
        self._core_app = CoreApplication(self)

        self._core_app._init()
        gag = ApplicationGroup('', self._global_config, no_ambient, no_app, app_names, self)
        self._global_app = gag._apps[0]
        self._global_app.finish_setup()
        # アプリケーショングループの順序は rc.caty の実行順序に関わる
        self._app_groups = []
        gdirs = glob('*.group')
        if not 'main.group' in gdirs:
            gdirs.append('main.group')
            # throw_caty_exception('ApplicationGroupNotFound', u'$grpName', grpName='main')
        for g in gdirs:
            name = g.split('.')[0]
            self._app_groups.append(ApplicationGroup(name, self._global_config, no_ambient, no_app, app_names, self))
        if is_debug:
            caty.DEBUG = True
        self.__debug = is_debug
        self._init_app_map()
        for grp in self._app_groups:
            for app in grp.apps:
                app.finish_setup()

        #for app in self._app_map.values():
        #    app.finish_setup()
        for group in self._app_groups:
            group.exec_rc_script()
        self.__cout = cout

    def _init_app_map(self):
        self._app_map = {}
        for grp in self._app_groups:
            for app in grp.apps:
                if app.name in self._app_map:
                    raise Exception(self.i18n.get('Application name conflicted: $name', name=app.name))
                self._app_map[app.name] = app
        self._app_map[u'global'] = self._global_app
        self._app_map[u'caty'] = self._core_app

    def get_app(self, app_name):
        from caty.core.exception import throw_caty_exception
        if app_name not in self._app_map:
            throw_caty_exception('ApplicationNotFound', u'$appName', appName=app_name)
        app = self._app_map[app_name]
        return app

    def get_apps(self):
        return self._app_map.values()

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
        self._deprecate_logger = syslog.get_deprecate_log()
    
    @property
    def access_logger(self):
        return self._access_logger

    @property
    def error_logger(self):
        return self._error_logger

    @property
    def deprecate_logger(self):
        return self._deprecate_logger

    @property
    def casm(self):
        return self._casm

    @property
    def app_names(self):
        return [a.name for a in self.get_apps() if a.name != 'caty']

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
    

    @property
    def system_resource_actions(self):
        return self._core_app._system_resource_actions

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
        self._global_app.reload()

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

    def init_app(self, name):
        grp = None
        if name == 'global':
            self._global_app.reload()
            return
        if name == 'caty':
            self.cout.writeln(self.i18n.get('$name can not be re-initialized manually', name=name))
            return
        for g in self._app_groups:
            if g.find_app(name):
                if grp:
                    self.cout.writeln(self.i18n.get('Application name conflicted: $name', name=name))
                    return
                else:
                    grp = g
        if not grp:
            self.cout.writeln(self.i18n.get(u'Application does not exists: $name', name=name))
            return None
        grp.init_app(name)
        self._init_app_map()

    def setup_app(self, name):
        grp = None
        if name == 'global':
            self._global_app.reload()
            return
        if name == 'caty':
            self.cout.writeln(self.i18n.get('$name can not be re-initialized manually', name=name))
            return
        for g in self._app_groups:
            if g.find_app(name):
                if grp:
                    self.cout.writeln(self.i18n.get('Application name conflicted: $name', name=name))
                    return
                else:
                    grp = g
        if not grp:
            self.cout.writeln(self.i18n.get(u'Application does not exists: $name', name=name))
            return None
        grp.setup_app(name)
        self._init_app_map()

    def remove_app(self, name):
        if name in ('caty', 'global'):
            self.cout.writeln(self.i18n.get('$name can not be removed', name=name))
            return
        grp = None
        for g in self._app_groups:
            if g.find_app(name):
                if grp:
                    self.cout.writeln(self.i18n.get('Application name conflicted: $name', name=name))
                    return
                else:
                    grp = g
        if not grp:
            self.cout.writeln(self.i18n.get(u'Application does not exists: $name', name=name))
            return None
        grp.remove_app(name)
        self._init_app_map()

    def finalize(self):
        for app in self.get_apps():
            app.finalize()

    def get_hcon_url(self):
        if self.hcon_name == self.hcon_port == None:
            return None
        if self.hcon_port:
            from urlparse import urlsplit
            r = urlsplit(self._global_config.host_url)
            return '%s://%s:%s' % (r.scheme, r.netloc.split(':')[0], self.hcon_port)
        elif self.hcon_name:
            return '%s/%s' % (self._global_config.host_url, self.hcon_name)

    def get_uuserver_url(self):
        if self.uuserver_port == None:
            return None
        from urlparse import urlsplit
        r = urlsplit(self._global_config.host_url)
        return '%s://%s:%s' % (r.scheme, r.netloc.split(':')[0], self.uuserver_port)

class CoreApplication(Application):
    def __init__(self, system):
        self._name = u'caty'
        self._system = system
        self._schema_fs = None
        self._command_fs = None
        self.parent = None
        self._deprecated = False
        self._annotations = {}
        self._description = u'Caty Core System'
        self._more_description = None
        self._global_config = system._global_config
        self._group = DummyGroup(self)
        self._system_resource_actions = []
        self.i18n = system.i18n
        self._facility_classes = {}
        self._master_entities = {}
        self._facilities_conf = {}
        self._backend_conf = {}
        self._loaded = True

    def _init(self):
        self._system.cout.writeln(self.i18n.get('Loading system data'))
        mafs_init = lambda type, path: self._global_config.mafs_initializer(self, self._system, type)('python', path, {}, self._system.appencoding)
        try:
            runtime_manifest = xjson.loads(open('python/app-manifest.xjson').read())
        except:
            self._system.cout.writeln(u'[Warning] ' + self.i18n.get(u'app-manifest of Caty Core is not found or invalid'))
            runtime_manifest = {
              "description": "Caty Core",
              "assign": {
                  "commands": "caty/core/std/command",
                  "schemata": "caty/core/std/schema",

                  "behaviors": None,
                  "messages": None,
                  "actions": None,
                  "pub": None,
                  "scripts": None,
                  "include": None,
                  "data": None,
                  "lib": "lib",
              },
            }
        schema_fs = mafs_init('schemata', runtime_manifest['assign']['schemata']).start()
        modules = []
        for e in schema_fs.opendir('/').read():
            if e.path.endswith('.casm') or e.path.endswith('.casm.lit'):
                modules.append(e.basename.split('.')[0])
        if 'builtin' in modules:
            modules.remove('builtin')
        self._system._casm = casm.initialize(self._system, modules, node)
        self._schema_module = self._system._casm._core
        self._web_path = u''
        self._interpreter = script.initialize(self._schema_module, self, self._system)
        self._dispatcher = self._create_system_dispatcher()
        self._extract_casm_from_cara()
        self._schema_module.resolve()

    def _extract_casm_from_cara(self):
        for mod in self._dispatcher.get_modules():
            if u'.' not in mod.canonical_name:
                self._schema_module.add_sub_module(mod)

    def _create_system_dispatcher(self):
        from caty.core.action.module import ResourceModuleContainer, ResourceModule
        from caty.core.std.action import create_default_resources
        self._system.cout.write(self._system.i18n.get(u'Initializing default resource classes...'))
        rm = ResourceModule(u'resources', u'Caty Default Resource Classes', self)
        rmc = ResourceModuleContainer(self)
        create_default_resources(rm)
        rmc.add_module(rm)
        for r in rm.resources:
            self._system_resource_actions.append(r)
        self._system.cout.writeln(u'OK')
        return rmc

    def create_facilities(self, session_maker=None):
        from caty.session.value import create_variable
        from caty.env import Env
        env = Env().create('uses')
        finder = self._schema_module.schema_finder.start()
        facilities = {
            'env': env,
            'schema': finder,
        }
        fset = FacilitySet(facilities, self)
        facilities['interpreter'] = self._interpreter.file_mode(fset)
        return fset

    def finish_setup(self):
        pass

    def __invariant__(self):
        pass


    def finalize(self):
        pass

class DummyGroup(object):
    def __init__(self, coreapp):
        self.name = u''
        self.apps = [coreapp]
        self.global_config = coreapp._global_config

    def __nonzero__(self):
        return False
