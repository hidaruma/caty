#coding: utf-8
from caty.core.schema.base import NullSchema
from caty.jsontools import stdjson
from caty.util import debug, brutal_encode
from caty.util.optionparser import OptionParser, OptionParseFailed
import caty.core.runtimeobject as ro
from caty.core.command.param import Option
from caty.core.command import new_dummy, Syntax
from caty.core.schema.base import UndefinedSchema
import types
from itertools import *
from functools import *

class ProfileContainer(object):
    u"""複数の CommandProfile をまとめるクラス。
    オプション引数位置固定引数で CommandProfile を決定する。
    入出力の型がオーバーロードされている場合、
    その後の処理は CommandProfile で行う。
    """
    def __init__(self, name, uri, commands, annotations, doc, app, module):
        self.profiles = []
        self.name = name
        path = (uri.split(':')[-1])
        if path == 'caty.core.command.Dummy':
            self.command_class = new_dummy()
        else:
            pkgname, cmdname = path.rsplit('.', 1)
            self.command_class = commands.get(pkgname, cmdname)
        self._annotations = annotations or {}
        self.doc = doc if doc else 'undocumented'
        self.defined_application = app
        self.uri = uri
        self.module = module
        self.type_params = []

    def accept(self, cursor):
        return cursor._visit_profile(self)

    def get_annotations(self):
        return self._annotations#[a.strip() for a in self.annotation.split(',')]

    @property
    def annotations(self):
        return self._annotations

    def add_profile(self, profile):
        self.profiles.append(profile)

    def determine_profile(self, opts_ref, args_ref):
        lasterror = None
        last_tb = None
        err_msg = ''
        for p in self.profiles:
            err_msg = p.conform_opts_and_args(opts_ref, args_ref, self.name)
            if not err_msg:
                return p.clone()
        else:
            raise CommandUsageError(err_msg, self)

    def get_command_class(self):
        return self.command_class

    def check_type_variable(self):
        msg = []
        for p in self.profiles:
            v = p.declobj.verify_type_var(self.type_var_names)
            if v is not None:
                msg.append(u'%sは%sで宣言されていない型変数です' % (v, self.name))
                
        if msg:
            raise JsonSchemaError('\n'.join(msg))

    def set_arg0_type(self, type):
        for p in self.profiles:
            if not u'static' in self._annotations:
                p.set_arg0_type(type)

    def resolve(self, module):
        for p in self.profiles:
            p.resolve()



class CommandProfile(object):
    u"""コマンドの引数や型の宣言を定義するクラス。
    一つのコマンドが複数の引数タイプなどでオーバーロードされるため、
    このクラス経由でコマンド確定時の入出力のスキーマを決定する。
    また、以下のようにコマンドの型宣言には複数の入出力のプロファイルがありうる。

        command foo {} [] :: null -> string,
                             string -> string
                             uses some_facility;

    この場合入力が null のものがデフォルトで採用される。
    また、プロファイルが一つしかない場合は常にそのプロファイルを利用する。
    """
    def __init__(self, opts_schema, args_schema, declobj):
        self.opts_schema = opts_schema
        self.args_schema = args_schema
        self.declobj = declobj
        self.resolved = False
        self._in_schema, self._out_schema = declobj.profile
        self.__arg0_schema = UndefinedSchema()
    
    def clone(self):
        n = CommandProfile(self.opts_schema, self.args_schema, self.declobj)
        n.set_arg0_type(self.__arg0_schema)
        return n

    @property
    def in_schema(self):
        return self._in_schema

    @property
    def out_schema(self):
        return self._out_schema

    @property
    def arg0_schema(self):
        return self.__arg0_schema

    def set_arg0_type(self, type):
        self.__arg0_schema = type

    def convert(self, value):
        u"""型変換処理。
        Caty のコマンドオブジェクトは複数のプロファイルを持ちうるため、
        このメソッドでは取りうるプロファイルについて総ざらいに変換処理を行い、
        成功した時点でプロファイルを確定する。
        """
        lasterror = None
        for i, o in self.declobj.profiles:
            try:
                v = i.convert(value)
                self._in_schema = i
                self._out_schema = o
                return v
            except Exception, e:
                raise

    def validate(self, value):
        u"""妥当性検証処理。
        基本的に convert と同様。
        """
        for i, o in self.declobj.profiles:
            try:
                i.validate(value)
                self._in_schema = i
                self._out_schema = o
                return
            except Exception, e:
                raise

    @property
    def facilities(self):
        u"""使用を宣言されたリソース(=Catyファシリティ)の名前を返す。
        """
        return self.declobj.get_all_resources()

    def conform_opts_and_args(self, opts_ref, args_ref, name):
        u"""オプションと引数が適合するかどうかを判別する。
        この時点では変数参照が解決されていないため、オプション名と引数の数のみで判別する。
        """
        if self.opts_schema.type == 'null' and opts_ref:
            return ro.i18n.get(u'$name takes no options', name=name)
        if self.opts_schema.type == 'object':
            o_s = self.opts_schema.schema_obj
            has_wildcard = self.opts_schema.wildcard.type != 'never'
            key_set = set(o_s.keys())
            found_key = set()
            for opt in opts_ref:
                if opt.type == 'glob': continue
                if opt.key not in o_s and not has_wildcard:
                    return ro.i18n.get('Unknwon option: $key', key=opt.key)
                found_key.add(opt.key)
            for k in key_set - found_key:
                if not o_s[k].optional:
                    return ro.i18n.get(u'Missing option: $key', key=k)
                else:
                    if 'default' in o_s[k].annotations:
                        opts_ref.append(Option(k, o_s[k].annotations['default'].value))
        if self.args_schema.type == 'null' and args_ref:
            return ro.i18n.get(u'$name takes no arguments', name=name)
        if self.args_schema.type == 'array':
            max_len = len(self.args_schema.schema_list) if not self.args_schema.repeat else None
            min_len = (len(filter(lambda s: not s.optional, self.args_schema.schema_list)) 
                        - int(self.args_schema.repeat))
            if max_len is not None and len(args_ref) > max_len:
                return ro.i18n.get(u'$name takes only the arguments up to $max', max=max_len, name=name)
            if min_len > len(args_ref):
                return ro.i18n.get(u'$name requires $min or more arguments', min=min_len, name=name)
        return u''

    def get_command_class(self):
        return self.declobj.get_command_class()

    def apply(self, node, module):
        from caty.core.casm.cursor.typevar import TypeVarApplier
        tc = TypeVarApplier(module)
        tc._init_type_params(node)
        tc.real_root = False
        i = self._in_schema.accept(tc)
        o = self._out_schema.accept(tc)
        return i, o

def check_enum(t, name, option, opt_str, value, parser):
    from caty.core.casm.cursor import TreeDumper
    td = TreeDumper()
    try:
        value = t.convert(value)
    except:
        raise OptionParseFailed('%s not in %s' % (str(value), td.visit(t)))
    setattr(parser.values, option.dest, value)

class ScriptProfileContainer(ProfileContainer):
    def __init__(self, name, proxy, commands, annotations, doc, app, module):
        self.profiles = []
        self.name = name
        self.command_class = proxy
        self._annotations = annotations or {}
        self.doc = doc if doc else 'undocumented'
        self.defined_application = app
        self.uri = ''
        self.type_params = []
        self.module = module
        self.command_class.set_module(module)

class CommandUsageError(Exception): pass

