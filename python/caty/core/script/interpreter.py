#coding: utf-8
from caty.core.command.exception import *
import caty.util as util
from caty import UNDEFINED

class BaseInterpreter(object):
    def visit(self, node):
        return node.accept(self)

    def visit_command(self, node):
        raise NotImplementedError('%s#visit_command' % self.__class__.__name__)

    def visit_pipe(self, node):
        raise NotImplementedError('%s#visit_pipe' % self.__class__.__name__)

    def visit_discard_pipe(self, node):
        raise NotImplementedError('%s#visit_discard_pipe' % self.__class__.__name__)

class CommandExecutor(BaseInterpreter):
    def __init__(self, cmd):
        self.cmd = cmd

    def __call__(self, input):
        self.input = input
        return self.cmd.accept(self)

    def visit_command(self, node):
        input = self.input
        if 'deprecated' in node.annotations:
            util.cout.writeln(u'[DEBUG] Deprecated: %s' % self.name)
        if node._mode: # @console など、特定のモードでしか動かしてはいけないコマンドのチェック処理
            mode = node.env.get('CATY_EXEC_MODE')
            if not node._mode.intersection(set(mode)):
                raise InternalException(u"Command $name can not use while running mode $mode", 
                                        name=node.profile_container.name,
                                        mode=str(mode)
                )
        try:
            node.var_storage.new_scope()
            node._prepare()
            node.in_schema.validate(input)
            if node.profile.in_schema.type == 'void':
                r = node.execute()
            else:
                r = node.execute(input)
            node.out_schema.validate(r)
            if 'commit-point' in node.profile_container.get_annotations():
                for n in node.facility_names:
                    getattr(node, n).commit()
            if isinstance(r, list):
                while r and r[-1] is UNDEFINED:
                    r.pop(-1)
            return r
        except Exception, e:
            if isinstance(e, PipelineInterruption) or isinstance(e, PipelineErrorExit):
                raise
            util.cout.writeln(u"[DEBUG] Error: " + repr(node))
            raise
        finally:
            node.var_storage.del_scope()

    def visit_pipe(self, node):
        self.input = node.bf.accept(self)
        return node.af.accept(self)

    def visit_discard_pipe(self, node):
        node.bf(self.input)
        self.input = None
        return node.af.accept(self)

    @property
    def in_schema(self):
        return self.cmd.in_schema

    @property
    def out_schema(self):
        return self.cmd.out_schema
