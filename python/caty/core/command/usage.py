#coding: utf-8

class CommandUsage(object):
    def __init__(self, profile_container):
        self.pc = profile_container

    def get_type_info(self):
        r = []
        for p in self.pc.profiles:
            opts, args, input, output = self.profile_usage(p)
            type_vars = ', '.join(map(lambda x:'<%s>' % x, self.pc.type_var_names))
            if opts:
                r.append('Usage: %s%s OPTION %s' % (self.pc.name, type_vars, args))
                r.append('Option:\n%s' % self.indent(opts))
            else:
                if args == 'null':
                    r.append('Usage: %s%s' % (self.pc.name, type_vars))
                else:
                    r.append('Usage: %s%s %s' % (self.pc.name, type_vars, args))
            r.append('Input:\n%s' % self.indent(input))
            r.append('Output:\n%s' % self.indent(output))
            r.append('\n')
        return '\n'.join(r)

    def get_usage(self):
        return self.get_type_info() + 'Description:\n' + self.get_doc()

    def get_doc(self):
        return self.pc.doc

    @property
    def title(self):
        return self.pc.doc.splitlines()[0].strip()

    def indent(self, s):
        r = []
        for l in s.splitlines():
            r.append('    ' + l)
        return '\n'.join(r)

    def profile_usage(self, prof):
        opt = TreeDumper().visit(prof.opts_schema)
        arg = ArgDumper().visit(prof.args_schema)
        inp = MiniDumper().visit(prof.in_schema)
        out = MiniDumper().visit(prof.out_schema)
        return opt, arg, inp, out



from caty.core.casm.cursor.dump import TreeDumper
class ArgDumper(TreeDumper):
    def _process_option(self, node, buff):
        if node.options:
            items = [(k, v) for k, v in node.options.items() if k not in ('subName', 'minCount', 'maxCount')]
            if 'subName' in node.options:
                buff.append(' ' + node.options['subName'])

class MiniDumper(TreeDumper):
    def _visit_root(self, node):
        return node.name


