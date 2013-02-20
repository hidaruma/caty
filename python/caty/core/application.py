#coding: utf-8
from caty.core.async import AsyncQueue
from caty.core.facility import Facility, AccessManager, FakeFacility, ReadOnlyFacility, EntityProxy, AbstractEntityProxy
from caty.util import cout, error_to_ustr, brutal_error_printer
from caty.util.path import join
from caty import mafs, storage, session
from caty.jsontools import xjson
from caty.util.collection import merge_dict
from caty.core.globalconf import *
from caty.core import script, casm
from caty.core.facility import (Facility,
                                FakeFacility,
                                FacilitySet,
                                AccessManager)
from caty.core.memory import AppMemory
from caty.core.std.command.authutil import (RequestToken,
                                            CATY_USER_INFO_KEY,
                                            CATY_USER_INFO_KEY)

from caty.core.customimporter import AppSpecLibraryImporter
from caty.core.exception import throw_caty_exception
from caty.util.collection import ImmutableDict
from caty.util import cout, error_to_ustr, brutal_error_printer
from caty.vcs import BaseClient
from caty.core.i18n import I18nMessage
from caty.core.action.dispatcher import resource_class_from_assocs, ResourceActionEntry
import caty.core.runtimeobject
import caty.core.logger as logger

from copy import deepcopy
from operator import truth as _
import locale
import codecs
import operator
import os
import platform
import sys
import time
import tempfile
RC_SCRIPT = u'/rc.caty'
RC_ONCE_SCRIPT = u'rc-once'
RC_DONE = u'rc-done'
RESERVED = set(['this', u'global', u'caty'])
ROOT = 'root'
USER = 'main'
LOG_TYPES = ['app', 'performance', 'exec']

class Application(object):
    u"""Caty アプリケーションオブジェクト。
    Caty アプリケーションは自身に特有なファイルシステム、スキーマ、コマンドなどを格納し、
    外部からの入力に応答して出力を返すオブジェクトである（実際の主たる処理は interpreter に委譲する）。

    Caty アプリケーションは他のアプリケーションの参照を行うため、
    互いへの参照を内部的には持っている。
    ただしそれはあくまでも特別なリソースアクセスのために行う事なので、
    基本的に Caty アプリケーション同士は分離された状態で動作する。
    """
    def __init__(self, name, no_ambient, group, system):
        u"""Caty アプリケーションの初期化はブートストラップで行う。
        最初は単にアプリケーション名を設定し、内部的な状態を初期化するだけである。
        """
        self._initialized = False
        self._no_ambient = no_ambient
        self._physical_path = join(group.path, name)
        self.importer = AppSpecLibraryImporter(os.path.abspath(self._physical_path))
        sys.meta_path.append(self.importer) # {$apDir}/libの読み込みに使う
        self._loaded = False
        self._initialize(name, group, system)
        self._initialized = True

    def _initialize(self, name, group, system):
        self._name = unicode(name)
        self._system = system
        self._path = unicode(name)
        self._facility_classes = {}
        self._facilities = {}
        self._group = group
        self._finished = False
        self._app_map = {name: self}
        self._global_config = group.global_config
        system.cout.writeln(system.i18n.get("Loading $name", name=self._path))
        self._configure()
        self.set_parent(system)
        if not self._disabled or system.force_app == name:
            self._init_filetype()
            self._init_mafs()
            self._init_msg()
            self._init_appdirs()
            self._init_schema()
            self._init_session()
            self._init_storage()
            self._init_vcs()
            self._init_memory()
            self._init_log()
            self._init_interpreter()
            self._init_action()
        else:
            self.cout.writeln(u'* ' + system.i18n.get("$name is set not to start", name=self._name))
        self.async_queue = AsyncQueue(self)
        self._lock_set = set()

    def set_parent(self, system):
        system._global_app.importer.add_child(self)
        self.parent = system._global_app

    def reload(self, module_name=None):
        self._no_ambient = False
        self.importer.discard()
        self._initialize(self._name, self._group, self._system)
        self.finish_setup()
        self.exec_rc_script()

    def force_load(self, module_name):
        import traceback
        from caty.core.casm.module import InMemoryModule
        from caty.util.path import is_mafs_path
        self._system.casm._core.clear_namespace()
        self.parent._schema_module.clear_namespace()
        self._schema_module.clear_namespace()
        error = False
        try:
            if is_mafs_path(module_name):
                path = module_name
                if '@' in path:
                    place, path = path.split('@', 1)
                else:
                    place = u'data'
                if path.startswith('this:'):
                    path = path.replace('this:', '')
                mafs = getattr(self, place)
                imm = InMemoryModule(self, self._schema_module)

                msg = self.i18n.get('Schema: $path', path=module_name)
                self.cout.write(u'  * ' + msg)
                imm.compile(mafs.start().open(path).read())
                self.cout.writeln(u'OK')
                self._schema_module.sub_modules[imm.name] = imm
            else:
                self._schema_module.load_on_demand(module_name)
        except:
            if is_mafs_path(module_name):
                self.cout.writeln(u'NG')
            error = True
            self.cout.writeln(traceback)
        finally:
            if error:
                self.cout.writeln(self.i18n.get(u'Failed to force-load. Reloading system data'))
            try:
                self.reinit_schema()
                self._loaded = True
            except:
                self.cout.writeln(traceback)
                self.cout.writeln(self.i18n.get(u'Failed to force-load. Reloading system data'))
                if not is_mafs_path(module_name):
                    self._schema_module.discard_module(module_name)

                self._system.casm._core.clear_namespace()
                self.parent._schema_module.clear_namespace()
                self._schema_module.clear_namespace()
                self.reinit_schema()
            self.reinit_interperter()

    def reinit_schema(self):
        if self.parent:
            self.parent.reinit_schema()
        self.cout.writeln('  * ' + self.i18n.get(u'Reconfiguring schema: $name', name=self.name))
        self._schema_module.resolve()

    def reinit_interperter(self):
        if self.parent:
            self.parent.reinit_interperter()
        self._init_interpreter()

    def exec_rc_script(self):
        if self._disabled:
            return
        if self._no_ambient:
            return
        scripts = self._scripts.start()
        if isinstance(scripts, FakeFacility):
            return
        if not scripts.open(RC_SCRIPT).exists:
            return
        self.cout.writeln(self.i18n.get("Running init script of $name", name=self.name))
        facilities = self.create_facilities()
        interpreter = self.interpreter.file_mode(facilities)
        modes = [unicode('console')]
        self.init_env(facilities, self._system.debug, modes, self._system, {'PATH_INFO': u'/'})
        try:
            interpreter.build(u'call ' + RC_SCRIPT)(None)
        except Exception, e:
            import traceback
            self.cout.writeln(traceback.format_exc())
            self.cout.write(error_to_ustr(e))
            self.i18n.write("An error occuered while running init script of $name", name=self.name)
        facilities._facilities.clear()

    def exec_rc_once_script(self):
        if self._disabled:
            return
        if self._no_ambient:
            return
        scripts = self._scripts.start()
        if isinstance(scripts, FakeFacility):
            return
        if not scripts.opendir('/' + RC_ONCE_SCRIPT).exists:
            return
        d = scripts.opendir('/' + RC_ONCE_SCRIPT)
        for f in d.read(True):
            if not f.path.endswith('.caty') or f.path.count('.') != 1:
                continue
            facilities = self.create_facilities()
            interpreter = self.interpreter.file_mode(facilities)
            modes = [unicode('console')]
            self.init_env(facilities, self._system.debug, modes, self._system, {'PATH_INFO': u'/'})
            try:
                self.i18n.write("Running $path of $name", path=f.path, name=self.name)
                interpreter.build('call ' + f.path)(None)
            except Exception, e:
                import traceback
                self.cout.writeln(traceback.format_exc())
                self.cout.write(error_to_ustr(e))
                self.i18n.write("An error occuered while running rc-once of $name", name=self.name)
                self._system.error_logger.error(self.i18n.get("An error occuered while running rc-once of $name", name=self.name) + ':' + traceback.format_exc())
                raise
            s = scripts.open(f.path)
            import time
            if not scripts.opendir('/rc-done').exists:
                scripts.opendir('/rc-done').create()
            s.rename('/rc-done/%s.%s.caty' % (f.basename.rsplit('.', 1)[0], time.strftime('%Y%m%d%H%M%S')))
            facilities._facilities.clear()
        scripts.commit()

    def add_app(self, app):
        if app.name in app:
            raise Exception(self.i18n.get("Application name conflicted: $name", name=app.name))
        self._app_map[app.name] = app

    def get_app(self, name):
        if name == 'this':
            return self
        return self._system.get_app(name)

    def release(self, key):
        try:
            import fcntl
            with open(sys.argv[0]) as f:
                fcntl.flock(lockFile.fileno(), fcntl.LOCK_EX)
                self._release(key)
        except:
            fcntl = None
            self._release(key)

    def _release(self, key):
        try:
            self._lock_set.remove(key)
        except:
            pass

    def _configure(self):
        cfg = self._verify_config(self._read_config())
        self._disabled = cfg['disabled']
        self._description = cfg['description']
        self._more_description = cfg.get('moreDescription', None)
        self._implLang = cfg['implLang']
        self._assgin = cfg['assign']
        self._indexfiles = cfg.get('indexFiles', ['index.html', 'index.htm', 'index.cgi', 'index.act'])
        self._filetypes = cfg.get('filetypes', {})
        self._encoding = cfg.get('encoding', 'utf-8')
        self._mime_types = self._global_config.mime_types
        self._raw_associations = self._global_config.associations
        self._site_path = self._name
        self._hosturl = self._global_config.host_url
        self._server_module_name = self._global_config.server_module_name
        self._app_spec = AppConfig()
        self._app_spec.update(cfg.get('appProp', {}))
        self._annotations = cfg.get('anno', {})
        self._deprecated = cfg.get('deprecated', False)
        self._manifest = cfg
        self._lock_wait_limit = cfg.get('lockWaitLimit', 60)

    def _read_config(self):
        app_dir = self._group._make_super_root(join(self._group.path, self.name)).start()
        f = app_dir.create(u'reads').open('/_manifest.xjson')
        if f.exists:
            try:
                cfg = xjson.loads(f.read())
            except Exception, e:
                self._system.i18n.write(u'Failed to parse JSON: $path\n$error', path=f.path, error=error_to_ustr(e))
                raise
            self._system.deprecate_logger.warning(u'%s: _manifest.xjson is deprecated.' % self.name)
        else:
            f = app_dir.create(u'reads').open('/app-manifest.xjson')
            if f.exists:
                try:
                    cfg = xjson.loads(f.read())
                except Exception, e:
                    self._system.i18n.write(u'Failed to parse JSON: $path\n$error', path=f.path, error=error_to_ustr(e))
                    raise
            else:
                cfg = self.default_conf()
        manifest_type = self._system._casm._core.schema_finder.get_type('AppManifest')
        manifest_type.validate(cfg)
        cfg = manifest_type.fill_default(cfg)
        ft = app_dir.create(u'reads').open('/_filetypes.xjson')
        if ft.exists:
            try:
                ft = xjson.loads(ft.read())
            except Exception, e:
                self.i18n.write(u'Failed to parse JSON: $path\n$error', path=ft.path, error=error_to_ustr(e))
        else:
            ft = {}
        if 'filetypes' in cfg:
            cfg['filetypes'] = merge_dict(cfg['filetypes'], ft)
        else:
            if ft:
                cfg['filetypes'] = ft
        if 'missingSlash' not in cfg:
            cfg['missingSlash'] = u'redirect'
        return cfg

    def _init_msg(self):
        try:
            msg = self._load_messages()
            self.i18n = self._system.i18n.extend(msg)
        except Exception, e:
            self.i18n = self._system.i18n

    def _load_messages(self):
        default_file = self._messages_fs.open('/default.xjson')
        try:
            base = xjson.loads(default_file.read()) if default_file.exists else []
        except Exception, e:
           self.i18n.write(u'Failed to parse JSON: $path\n$error', path='/default.xjson', error=error_to_ustr(e))
           raise
        msg = {}
        for m in base:
            msg[m] = {}
        languages = set([])
        for f in self._messages_fs.opendir('/').read():
            if not (f.path.endswith('.xjson') and f.path != '/default.xjson'):
                continue
            try:
                messages = xjson.loads(f.read())
            except Exception, e:
                self.i18n.write(u'Failed to parse JSON: $path\n$error', path=path, error=error_to_ustr(e))
                raise

            lang = f.path.split('/')[-1].split('.')[0]
            languages.add(lang)
            for e_msg, trans in messages.items():
                if e_msg not in msg:
                    if self._system.debug:
                        print '[DEBUG]', self._system.i18n.get('this message is not contained default.xjson: $message($lang)', message=e_msg, lang=lang)
                    msg[e_msg] = {lang: trans}
                else:
                    msg[e_msg][lang] = trans
                    
        for k, v in msg.items():
            for l in languages:
                if l not in v and self._system.debug:
                    print '[DEBUG]', self._system.i18n.get('this message is not translated: $message($lang)', message=k, lang=l)
        return msg

    def default_conf(self):
        return {
            'disabled': False,
            'description': u'%s' % self.name,
            'implLang': u"python",
            'assign': {
                'pub': u'pub',
                'include': u'include',
                'actions': u'actions',
                'commands': u'commands',
                'scripts': u'scripts',
                'schemata': u'schemata',
                'behaviors': u'behaviors',
                'data': u'data',
                'messages': u'messages',
            },
        }

    def _verify_config(self, obj):
        return merge_dict(obj, self.default_conf(), 'pre')

    def _init_appdirs(self):
        app_mafs = self._group._make_super_root(join(self._group.path, self._path)).start()
        app_dir = app_mafs.create(u'uses')
        generated = []
        for k in self._assgin.values() + ['lib']:
            d = app_dir.opendir('/' + k)
            if not d.exists:
                self.i18n.write("$location does not exists in $app, auto-generating", location=k, app=self.name)
                d.create()
                generated.append(k)
        app_mafs.commit()

    def _init_filetype(self):
        defined_assoc = set()
        for k, v in self._filetypes.items():
            assoc = v.get('assoc', None)
            if assoc:
                if '|' in k:
                    patterns = k.split('|')
                else:
                    patterns = [k]
                for p in patterns:
                    if p in defined_assoc:
                        self._raw_associations[p].update(assoc)
                    else:
                        self._raw_associations[p] = assoc
                        defined_assoc.add(p)
            it = v.get('isText', True)
            ct = v.get('contentType', u'text/plain' if it else u'application/octet-stream')
            ds = v.get('description', u'')
            t = {
                'isText': it,
                'contentType': ct,
                'description': ds,
            }
            keys = k.split('|')
            for a in keys:
                self._mime_types[a] = t

    def _init_mafs(self):
        root = join(self._group.path, self._path)
        assign = self._assgin
        mafs_init = lambda type, path: self._global_config.mafs_initializer(self, self._system, type)(root, path, self._mime_types, self._encoding)
        self._pub = mafs_init('pub', assign['pub'])
        self._include = mafs_init('include', assign['include'])
        self._actions = mafs_init('actions', assign['actions'])
        self._data = mafs_init('data', assign['data'])
        self._behaviors = mafs_init('behaviors', assign['behaviors'])
        self._command_fs = mafs_init('commands', assign['commands']).start().create(u'reads')
        self._schema_fs = mafs_init('schemata', assign['schemata']).start().create('reads')
        self._lib_fs = mafs_init('lib', 'lib').start().create('reads')
        self._messages_fs = mafs_init('messages', assign['messages']).start().create(u'reads')

  # スクリプトファイル
        _scripts = mafs_init('scripts', assign['scripts'])
        if _scripts:
            self._scripts = _scripts
        else:
            self._scripts = FakeFacility()

    def update_filetypes(self, filetypes):
        if filetypes:
            for k, v in filetypes.items():
                self._mime_types[k] = v

    def _init_schema(self):
        if self._no_ambient:
            self._schema_module = self._system.casm.make_blank_module(self)
        else:
            self._schema_module = self._system.casm.make_app_module(self)
  #self._schema_module.compile()

    def _init_interpreter(self):
        self._interpreter = script.initialize(self._schema_module, self, self._system)

    def _init_session(self):
        self._session_storage = self._global_config.session.storage

    def _init_storage(self):
        self._storage = storage.initialize(self._global_config.storage_conf)

    def _init_vcs(self):
        if self._global_config.vcs_module:
            self._vcs = self._global_config.vcs_module.VCSClient
        else:
            self._vcs = BaseClient

    def _init_memory(self):
        if not self._initialized:
            self._memory = AppMemory()

    def _init_log(self):
        if not self._initialized:
            for tp in LOG_TYPES:
                logger.init(self, tp)

    def register_facility(self, name, cls, system_param):
        if name in self._facility_classes:
            raise Exception(self.i18n.get("Facility name conflicted: $name at $app", name=name, app=self.name))
        self._facility_classes[name] = (cls, system_param)

    def register_entity(self, name, facility_name, user_param):
        if name in self._facility_classes:
            raise Exception(self.i18n.get("Entity name conflicted: $name at $app", name=name, app=self.name))
        if facility_name not in self._facility_classes:
            raise Exception(self.i18n.get("Unknown facility: $name at $app", name=name, app=self.name))
        cls, sys_param = self._facility_classes[facility_name]
        self._facility_classes[name] = (cls, sys_param, user_param, facility_name)

    def _init_facilities(self):
        initialized = set()
        for k, v in self._facility_classes.items():
            if v[0] is None:
                continue
            if v[0] in initialized:
                continue
            v[0].initialize(self, v[0].__system_config__)
            initialized.add(v[0])

    def get_logger(self, type):
        assert type in LOG_TYPES
        return logger.get(str(self.name), str(type))

    def _init_action(self):
        self._create_dispatcher() 
        self._create_bindings()  # ポートのバインド(cambの読み込み)

    def finish_setup(self):
        self.cout.writeln(self.i18n.get("Initializing '$name'", name=self.name))
        if self._disabled and self._system.force_app != self.name:
            return
        self._init_interpreter()  # 一旦インタープリターを初期化してスクリプトコンパイラが動くようにする
        c = {}
        c['indexfiles'] = self.indexfiles[:]
        c['script_ext'] = ['.cgi', '.act', '.do']
        c['missingSlash'] = self._manifest['missingSlash']
        self._web_config = ImmutableDict(c)
        try:
            if not self._no_ambient:
                self._schema_module.resolve()  # 型参照は最終的にここで解決される。
                self._binder.resolve(self._schema_module, self._dispatcher)
                self._init_facilities()        # カスタムファシリティの初期化
        except Exception, e:
  #msg = error_to_ustr(e)
  #cout.writeln(e)
            raise
        self._init_interpreter()  # ユーザ定義コマンドが解決されたので再度初期化
        self._init_mafs()  # action定義でファイルタイプが加わっている可能性があるので再度初期化。
        if self._no_ambient:
            return
        self._loaded = True
        if self._app_spec:
            if not '$typename' in self._app_spec:
                raise Exception(self.i18n.get("Schema for AppSpec is not specified: $app", app=self.name))
            tn = self._app_spec['$typename']
            cb = self._app_spec.get('$callback', None)
            tp = self._schema_module.schema_finder.start().get_type(tn)
            try:
                tp.validate(self._app_spec)
                self.__exec_callback(cb)
            except Exception, e:
                import traceback
                self.cout.writeln(traceback)
                self.cout.writeln(e)
                raise Exception(self.i18n.get("Failed to validate the AppSpec: $app", app=self.name))

    def _create_dispatcher(self):
        from caty.core.action import create_resource_action_dispatcher
        facilities = self.create_facilities()
        dispatcher = create_resource_action_dispatcher(self._actions.start().create(u'reads'), facilities, self)
        filetype_classes = resource_class_from_assocs(self._raw_associations, facilities, self)
        for c in filetype_classes:
            dispatcher.add_resource(c)
        self._dispatcher = dispatcher

    def _create_bindings(self):
        from caty.core.camb import create_bindings
        self._binder = create_bindings(self._actions.start().create(u'reads'), self)

    def __exec_callback(self, callback_class_name):
        import copy
        if not callback_class_name: return
        gd = {}
        modname, clsname = callback_class_name.rsplit('.', 1)
        exec 'from %s import %s as _callback' % (modname, clsname) in gd
        cb = gd['_callback'](self._app_spec.clone())

    def create_facilities(self, session_maker=None):
        from caty.session.value import create_variable
        from caty.env import Env
        env = Env().create(u'uses')
        stream = StreamWrapper(StdStream(self.sysencoding))
        finder = self._schema_module.schema_finder.start()
        facilities = {
            'pub': self._pub.start(),
            'env': env.start().create(u'uses'),
            'stream': stream.start(),
            'session': session_maker().start() if session_maker else self._session_storage.create().start(),
            'scripts': self._scripts.start(),
            'include': self._include.start(),
            'schema': finder,
            'data': self._data.start(),
            'storage': self._storage.set_finder(finder).start(),
            'behaviors': self._behaviors.start(),
            'schemata': self._schema_fs,
            'config': self._app_spec,
            'memory': self._memory.start(),
            'logger': logger.Logger(self).start(),
            'sysfiles': self._create_sysfiles(),
        }
        for k, v in self._facility_classes.items():
            try:
                if v[0] is None: continue
                if len(v) == 2:
                    facilities[k] = AbstractEntityProxy(v[0].instance(self, v[1]), None)
                else:
                    facilities[k] = EntityProxy(v[0].instance(self, v[1]), v[2])
            except:
                import traceback
                traceback.print_exc()
                self.cout.writeln(self.i18n.get(u'Failed to initialize facility class: $name', name=k))
                
        vcs = self._vcs(self, facilities['pub'], facilities['data'])
        facilities['vcs'] = vcs
        facilities['token'] = RequestToken(facilities['session'])
        fset = FacilitySet(facilities, self)
        facilities['interpreter'] = self._interpreter.file_mode(fset)
        return fset

    def has_facility(self, name):
        if name in self._facility_classes:
            return True
        reserved = set([
            'pub',
            'env',
            'stream',
            'session',
            'scripts',
            'include',
            'schema',
            'data',
            'storage',
            'behaviors',
            'schemata',
            'config',
            'memory',
            'logger',
            'sysfiles',
            'interpreter',
            'token',
            'vcs',
            'session',]
        )
        if name in reserved:
            return True
        return False

    def _create_sysfiles(self):
        return SysFiles(
            actions=self._actions.start().create(u'reads'),
            schemata=self._schema_fs.start().create(u'reads'),
            commands=self._command_fs.start().create(u'reads'),
            lib=self._lib_fs.start().create(u'reads'),
        )

    def init_env(self, facilities, is_debug, modes, system, environ={}):
        env = facilities['env']
        env.put(u'APP_ENCODING', unicode(self.encoding))
        env.put(u'SYS_ENCODING', unicode(self.sysencoding))
        env.put(u'APP_PATH', unicode(self.web_path))
        env.put(u'APPLICATION', {'group': self._group.name, 'description':self.description, 'name':self.name, 'path': unicode(self.web_path)})
        env.put(u'DEBUG', system.debug)
        env.put(u'HOST_URL', unicode(self.host_url))
        env.put(u'CATY_VERSION', unicode(caty.__version__))
        env.put(u'RUN_MODE', modes)
        env.put(u'PROJECT', {'name': self._system.project_name, 'location': unicode(os.getcwd(), self._system.sysencoding)})
        env.put(u'OS_PLATFORM', unicode(platform.system()))
        if 'CONTENT_TYPE' in environ:
            env.put(u'CONTENT_TYPE', unicode(environ['CONTENT_TYPE']))
        if 'PATH_INFO' in environ:
            env.put(u'PATH_INFO', unicode(environ['PATH_INFO']))
        if 'LANGUAGE' in environ:
            env.put(u'LANGUAGE', unicode(environ['LANGUAGE']))
        else:
            env.put(u'LANGUAGE', unicode(self._system._global_config.language))
        if environ.get('QUERY_STRING'):
            env.put(u'QUERY_STRING', u'?' + environ['QUERY_STRING'])
        else:
            env.put(u'QUERY_STRING', u'')
        if 'SERVER_SOFTWARE' in environ:
            env.put(u'SERVER_SOFTWARE', unicode(environ['SERVER_SOFTWARE']))
        env.put(u'SECURE', environ.get('X-Forwarded-Proto') == 'https')
        env.put(u'SERVER_MODULE', self._system.server_module_name)
        env.put(u'REQUEST_METHOD', unicode(environ.get('REQUEST_METHOD', 'POST')))
        env.put(u'CONTENT_LENGTH', unicode(environ.get('CONTENT_LENGTH', '-1')))
        env.put(u'HCON_URL', self._system.get_hcon_url())
        env.put(u'LOGGED', CATY_USER_INFO_KEY in facilities['session'])

    @property
    def cout(self):
        return self._system.cout

    @property
    def name(self):
        return self._name

    @property
    def encoding(self):
        return self._encoding

    @property
    def sysencoding(self):
        return self._global_config.sysencoding

    @property
    def web_path(self):
        return u'/%s' % self._name if self._name != ROOT else u''

    @property
    def description(self):
        return self._description

    @property
    def host_url(self):
        return self._global_config.host_url

    @property
    def associations(self):
        return self._associations

    @property
    def interpreter(self):
        return self._interpreter

    @property
    def indexfiles(self):
        return self._indexfiles

    @property
    def session_storage(self):
        return self._session_storage

    @property
    def pub(self):
        return self._pub

    @property
    def include(self):
        return self._include

    @property
    def data(self):
        return self._data

    @property
    def behaviors(self):
        return self._behaviors

    @property
    def scripts(self):
        return self._scripts

    @property
    def schema_finder(self):
        return self._schema_module.schema_finder

    @property
    def web_config(self):
        u"""Web からのアクセスに必要な設定項目
        """
        return self._web_config

    @property
    def enabled(self):
        return not self._disabled or self.name == self._system.force_app

    @property
    def verb_dispatcher(self):
        return self._dispatcher

    @property
    def resource_module_container(self):
        return self._dispatcher

    @property
    def deprecated(self):
        return self._deprecated

    @property
    def more_description(self):
        return self._more_description

    
    @property
    def manifest(self):
        return self._manifest

    def to_name_tree(self):
  # ネームツリーの各要素は
  # 各種mafs, JSONStorage, Session, Env, Memory
        r = {
            u'kind': u'c:app',
            u'id': self._name,
            u'childNodes': {},
        }
        d = r['childNodes']
        f = self.create_facilities()
        d['env'] = f['env'].to_name_tree()
        d['session'] = f['session'].to_name_tree()
        d['schema'] = f['schema'].to_name_tree()
        d['place'] = {
            u'kind': u'ns:place',
            u'id': self._name + '-' + u'place',
            u'childNodes': {
                'pub': f['pub'].to_name_tree(),
                'data': f['data'].to_name_tree()
            },
        }
  #d['storage'] = self._storage.to_name_tree()
  #    'pub': self._pub.start(),
  #    'scripts': self._scripts.start(),
  #    'include': self._include.start(),
  #    'schema': finder,
  #    'data': self._data.start(),
  #    'storage': self._storage.set_finder(finder).start(),
  #    'behaviors': self._behaviors.start(),
  #    'schemata': self._schema_fs,
  #    'config': self._app_spec,
  #    'memory': self._memory.start(),
  #    'logger': logger.Logger(self).start(),
  #    'sysfiles': self._create_sysfiles(),
        for k, v in f.items():
            v.cancel()
        return r

    def finalize(self):
        for f in set([v[0] for v in self._facility_classes.values()]):
            if f:
                f.finalize(self)

class StdStream(object):
    def __init__(self, encoding):
        self.encoding = encoding
        self.out = codecs.getwriter(self.encoding)(sys.stdout)
        self.input = codecs.getwriter(self.encoding)(sys.stdin)

    def write(self, content):
        self.out.write(content)

    def read(self):
        return xjson.loads(self.input.read())


class StreamWrapper(Facility):
    def __init__(self, stream):
        self.__stream = stream
        Facility.__init__(self)

    am = AccessManager()

    @am.update
    def write(self, content):
        self.__stream.write(content)

    @am.read
    def read(self):
        return self.__stream.read()

    @property
    def encoding(self):
        return self.__stream.encoding

    def clone(self):
        return self



INDEX_HTML = u"""
<?caty-meta template="smarty"?>
<html>
    <head>
        <title>Welcome</title>
    </head>
    <body>
        {include file="templates:/global_menu.html"}
        <h1>Welcome</h1>
    <!--
    This file is automatically generated by Caty.
    The file contains Japanese characters encoded in UTF-8.
    -->
        <p>Caty のサイトにようこそ。</p>

        <p>(これは、Caty によって自動生成されたファイルです。)</p>
        {include file="templates:/footer.html"}
    </body>
</html>
"""


class DummyApplication(Application):
    def __init__(self, system=None, name=u''):
        self._system = system
        self._name = name
        self.async_queue = AsyncQueue(self)
        self._lock_set= set()
        self.i18n = system.i18n if system else None


class AppConfig(dict, FakeFacility):
    def clone(self):
        n = AppConfig()
        for k, v in self.items():
            n[k] = deepcopy(v)
        return n


class SysFiles(Facility):
    def __init__(self, **kwds):
        self.__names = []
        for k, v in kwds.items():
            setattr(self, k, v)
            self.__names.append(k)

    def clone(self):
        return SysFiles(
            **dict([(n, getattr(self, n).clone()) for n in self.__names])
        )

    def create(self, mode, user_param=None):
        return SysFiles(
            **dict([(n, getattr(self, n).create(mode, user_param)) for n in self.__names])
        )

    def commit(self):
        for n in self.__names:
            getattr(self, n).commit()

    def cancel(self):
        for n in self.__names:
            getattr(self, n).cancel()

    def cleanup(self):
        for n in self.__names:
            getattr(self, n).cleanup()


class GlobalApplication(Application):
    def __init__(self, name, no_ambient, group, system):
        if not os.path.exists('global'):
            os.mkdir('global')
        self._initialized = False
        self._no_ambient = False  # 常にFalse
        self._physical_path = join(group.path, name)
        self.importer = AppSpecLibraryImporter(os.path.abspath(self._physical_path))
        sys.meta_path.append(self.importer) # {$apDir}/libの読み込みに使う
        self._initialize(name, group, system)
        self._initialized = True

    def reload(self):
        self._no_ambient = False
        self.importer.discard()
        self._initialize(self._name, self._group, self._system)
        self.finish_setup()
        self.exec_rc_script()

    def set_parent(self, system):
        self.parent = system._core_app
