#coding:utf-8
class ST(object):
    def accept(self, visitor):
        return visitor.visit(self)

    @property
    def type(self):
        return None

class Null(ST):

    @property
    def type(self):
        return 'Null'

    def __iter__(self):
        return iter([])

class Template(ST):
    def __init__(self, nodes, no_grouping=False):
        if no_grouping:
            self.nodes = nodes
        else:
            self.nodes = self._make_default_group(nodes)

    def _make_default_group(self, nodes):
        r = []
        default_group_node = []
        series_of_func_or_group_end = False
        for n in nodes:
            if (n.type == 'DefFunc' or n.type == 'DefGroup') and not series_of_func_or_group_end:
                default_group_node.append(n)
            else:
                if default_group_node:
                    r.append(DefGroup(None, default_group_node))
                    series_of_func_or_group_end = True
                    default_group_node = None
                r.append(n)
        if default_group_node:
            r.append(DefGroup(None, default_group_node))
            series_of_func_or_group_end = True
            default_group_node = None
        return r

    @property
    def type(self):
        return 'Template'


class String(ST):
    def __init__(self, s):
        self.data = s

    @property
    def type(self):
        return 'String'

class If(ST):
    def __init__(self, varnode, subtempl, elifnodes, elsenode):
        self.varnode = varnode
        self.subtempl = subtempl
        self.elifnodes = elifnodes
        self.elsenode = elsenode

    @property
    def type(self):
        return 'If'

class Elif(ST):
    def __init__(self, varnode, subtempl):
        self.varnode = varnode
        self.subtempl = subtempl
        self.upcoming_end_label = None

    @property
    def type(self):
        return 'Elif'

class Else(ST):
    def __init__(self, subtempl):
        self.subtempl = subtempl

    @property
    def type(self):
        return 'Else'

class For(ST):
    def __init__(self, loopitem, 
                       varnode, 
                       loopkey, 
                       index, 
                       iteration, 
                       counter,
                       first,
                       last,
                       subtempl,
                       elsetempl):
        self.loopitem = loopitem
        self.context = '__loop_' + loopitem
        self.varnode = varnode
        self.index = index
        self.iteration = iteration
        self.counter = counter
        self.first = first
        self.last = last
        self.loopkey = loopkey
        self.subtempl = subtempl
        self.elsetempl = elsetempl or Null()

    @property
    def type(self):
        return 'For'

class Include(ST):
    def __init__(self, name, context=''):
        self.filename = name
        self.context = context

    @property
    def type(self):
        return 'Include'

class VarLoad(ST):
    def __init__(self, name, undefinable=False):
        self.varname = name
        self.undefinable = undefinable

    @property
    def type(self):
        return 'Load'

class FilterCall(ST):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    @property
    def type(self):
        return 'Call'

class VarDisp(ST):
    def __init__(self):
        pass

    @property
    def type(self):
        return 'Disp'


class DefMacro(ST):
    def __init__(self, name, vars, sub_template):
        self.name = name
        self.vars = vars
        self.sub_template = sub_template

    @property
    def type(self):
        return 'DefMacro'

class ExpandMacro(ST):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    @property
    def type(self):
        return 'ExpandMacro'

class DefFunc(ST):
    def __init__(self, name, match, context_type, matched, sub_template):
        self.name = name if name is not None else str(id(self))
        self.match = match
        self.context_type = context_type
        self.sub_template = sub_template
        self.matched = matched

    @property
    def type(self):
        return 'DefFunc'

class CallFunc(ST):
    def __init__(self, name, context):
        self.name = name
        self.context = context

    @property
    def type(self):
        return 'CallFunc'

class DefGroup(ST):
    def __init__(self, name, member):
        self.name = name
        self.member = member

    @property
    def type(self):
        return 'DefGroup'

class CallGroup(ST):
    def __init__(self, name, context):
        self.name = name
        self.context = context

    @property
    def type(self):
        return 'CallGroup'
