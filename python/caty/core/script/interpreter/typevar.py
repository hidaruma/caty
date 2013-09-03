from caty.core.script.interpreter.base import BaseInterpreter
from caty.core.schema.base import TypeVariable
from caty.util.dev import debug

class TypeVarApplier(BaseInterpreter):
    def __init__(self, type_params):
        self.type_params = type_params

    def visit_command(self, node):
        node.apply_type_params(self.type_params)

    def visit_script(self, node):
        if not node.prepared:
            ta = []
            for i, t in enumerate(node.type_args):
                for p in self.type_params:
                    if p.var_name == t.name:
                        ta.append(p._schema if p._schema else p._default_schema if p._default_schema else p)
            if ta:
                node.apply_type_params(ta)
            return
        node.apply_type_params(self.type_params)
        if node.script:
            node.script.accept(self)

    def visit_pipe(self, node):
        node.bf.accept(self)
        node.af.accept(self)

    def visit_discard_pipe(self, node):
        node.bf.accept(self)
        node.af.accept(self)

    def visit_scalar(self, node):
        pass

    def visit_list(self, node):
        for n in node:
            n.accept(self)

    def visit_parlist(self, node):
        for n in node:
            n.accept(self)

    def visit_parobject(self, node):
        for k, v in node.items():
            v.accept(self)
        if node.wildcard:
            node.wildcard.accept(self)

    def visit_object(self, node):
        for k, v in node.items():
            v.accept(self)

    def visit_varstore(self, node):
        pass

    def visit_varref(self, node):
        pass

    def visit_argref(self, node):
        pass

    def visit_when(self, node):
        for c in node.cases.values():
            c.cmd.accept(self)

    def visit_binarytag(self, node):
        node.command.accept(self)

    def visit_unarytag(self, node):
        pass

    def visit_each(self, node):
        node.cmd.accept(self)

    def visit_time(self, node):
        node.cmd.accept(self)

    def visit_take(self, node):
        node.cmd.accept(self)

    def visit_start(self, node):
        node.cmd.accept(self)

    def visit_case(self, node):
        for c in node.cases:
            c.accept(self)

    def visit_begin(self, node):
        node.cmd.accept(self)
    
    def visit_repeat(self, node):
        pass

    def visit_json_path(self, node):
        pass

    def visit_try(self, node):
        node.pipeline.accept(self)

    def visit_unclose(self, node):
        node.pipeline.accept(self)

    def visit_choice_branch(self, node):
        for c in node.cases:
            c.accept(self)
