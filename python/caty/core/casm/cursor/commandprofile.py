# coding: utf-8
from caty.core.casm.cursor.base import SchemaBuilder
from caty.core.casm.cursor.resolver import ReferenceResolver
from caty.core.casm.cursor.typevar import TypeVarApplier
from caty.core.casm.cursor.normalizer import TypeNormalizer
from caty.core.exception import CatyException
from caty.core.command.profile import CommandProfile, ProfileContainer, ScriptProfileContainer, BoundProfileContainer
from caty.core.schema import *

class ProfileBuilder(SchemaBuilder):

    def _visit_function(self, node):

        self._root_name = node.name
        if node.profile_container: # register-public時に処理が二重に走らないように
            return node.profile_container
        if u'bind' in node.annotations and self.module.is_class: # メソッドの自動バインド
            pc = BoundProfileContainer(node.name, 
                                  self.module.uri.get('python', ''), 
                                  node.annotation, 
                                  node.doc, 
                                  node.application, 
                                  self.module)
        elif node.uri:
            pc = ProfileContainer(node.name, 
                                  node.uri, 
                                  self.module.command_loader, 
                                  node.annotation, 
                                  node.doc, 
                                  node.application, 
                                  self.module)
        else:
            pc = ScriptProfileContainer(node.name, 
                                        node.script_proxy, 
                                        self.module.command_loader, 
                                        node.annotation, 
                                        node.doc, 
                                        node.application, 
                                        self.module)

        for pat in node.patterns:
            pat = pat.clone() # 不変オブジェクトになっていないのでクローンで元のデータを保護
            rr = ReferenceResolver(self.module)
            params = []
            # 型パラメータのデフォルト値を設定
            for p in node.type_params + self.module.type_params:
                schema = TypeVariable(p.var_name, [], p.kind, p.default, {}, self.module)
                params.append(schema.accept(rr))
            self._type_params = params
            pc.type_params = params
            pat.build([self, rr])
            e = pat.verify_type_var(node.type_var_names + [t.var_name for t in self.module.type_params])
            if e:
                raise CatyException(u'SCHEMA_COMPILE_ERROR', 
                                    u'Undeclared type variable at $this: $name',
                                    this=node.name, name=e)
            tc = TypeVarApplier(self.module)
            tn = TypeNormalizer(self.module)
            tc.real_root = False
            tc._init_type_params(node)
            opt_schema = tn.visit(pat.opt_schema.accept(tc))
            tc._init_type_params(node)
            arg_schema = tn.visit(pat.arg_schema.accept(tc))
            p = pat.decl.profile
            new_prof = [None, None]
            tc._init_type_params(node)
            new_prof[0] = tn.visit(p[0].accept(tc)) 
            tc._init_type_params(node)
            new_prof[1] = tn.visit(p[1].accept(tc))
            pat.decl.profile = tuple(new_prof)
            pc.add_profile(CommandProfile(pat.opt_schema, pat.arg_schema, pat.decl))
        cmd = pc.get_command_class()
        cmd.profile_container = pc
        node.profile_container = pc
        return pc

    def _visit_profile(self, node):
        return node
