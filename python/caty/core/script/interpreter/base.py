class BaseInterpreter(object):
    def visit(self, node):
        return node.accept(self)

    def visit_command(self, node):
        raise NotImplementedError(u'{0}#visit_command'.format(self.__class__.__name__))

    def visit_pipe(self, node):
        raise NotImplementedError(u'{0}#visit_pipe'.format(self.__class__.__name__))

    def visit_discard_pipe(self, node):
        raise NotImplementedError(u'{0}#visit_discard_pipe'.format(self.__class__.__name__))

    def visit_scalar(self, node):
        raise NotImplementedError(u'{0}#visit_scalar'.format(self.__class__.__name__))

    def visit_list(self, node):
        raise NotImplementedError(u'{0}#visit_list'.format(self.__class__.__name__))

    def visit_object(self, node):
        raise NotImplementedError(u'{0}#visit_object'.format(self.__class__.__name__))

    def visit_varstore(self, node):
        raise NotImplementedError(u'{0}#visit_varstore'.format(self.__class__.__name__))

    def visit_varref(self, node):
        raise NotImplementedError(u'{0}#visit_varref'.format(self.__class__.__name__))

    def visit_argref(self, node):
        raise NotImplementedError(u'{0}#visit_argref'.format(self.__class__.__name__))

    def visit_when(self, node):
        raise NotImplementedError(u'{0}#visit_when'.format(self.__class__.__name__))

    def visit_binarytag(self, node):
        raise NotImplementedError(u'{0}#visit_binarytag'.format(self.__class__.__name__))

    def visit_unarytag(self, node):
        raise NotImplementedError(u'{0}#visit_unarytag'.format(self.__class__.__name__))

    def visit_each(self, node):
        raise NotImplementedError(u'{0}#visit_each'.format(self.__class__.__name__))

    def visit_time(self, node):
        raise NotImplementedError(u'{0}#visit_time'.format(self.__class__.__name__))

    def visit_take(self, node):
        raise NotImplementedError(u'{0}#visit_take'.format(self.__class__.__name__))

    def visit_script(self, node):
        raise NotImplementedError(u'{0}#visit_script'.format(self.__class__.__name__))

    def visit_start(self, node):
        raise NotImplementedError(u'{0}#visit_start'.format(self.__class__.__name__))

    def visit_case(self, node):
        raise NotImplementedError(u'{0}#visit_case'.format(self.__class__.__name__))

    def visit_begin(self, node):
        raise NotImplementedError(u'{0}#visit_begin'.format(self.__class__.__name__))

    def visit_repeat(self, node):
        raise NotImplementedError(u'{0}#visit_repeat'.format(self.__class__.__name__))
    
    def visit_json_path(self, node):
        raise NotImplementedError(u'{0}#visit_json_path'.format(self.__class__.__name__))
