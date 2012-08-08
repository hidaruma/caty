from caty.core.script.interpreter.base import BaseInterpreter


class TypeVarApplier(BaseInterpreter):
    def __init__(self, type_params):
        self.type_params = type_params

    def visit_command(self, node):
        node.apply_type_params(self.type_params)

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

    def visit_script(self, node):
        node.apply_type_params(self.type_params)
        if node.script:
            node.script.accept(self)

    def visit_start(self, node):
        node.cmd.accept(self)

    def visit_case(self, node):
        for c in node.cases:
            c.accept(self)

    def visit_json_path(self, node):
        pass


