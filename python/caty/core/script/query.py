
class Fetcher(object):
    def fetch_addr(self, ref, app, facilities, auto_extract=False):
        from caty.util.path import is_mafs_path
        from caty.core.command import VarStorage
        from caty.core.command.param import Option, Argument
        from caty.core.script.interpreter.executor import CommandExecutor
        from caty.core.script.builder import CommandBuilder
        from caty.core.facility import TransactionPendingAdaptor
        import caty.jsontools as json
        import caty.jsontools.selector as selector
        ref = json.untagged(ref)
        name = ref[u'type'] + '.get'
        raw_args = [ref[u'arg']]
        if u'ext' in ref and auto_extract:
            raw_args.append(ref[u'ext'])
        cmd_class = app._schema_module.get_command(name)
        opts = []
        args = []
        for v in raw_args:
            args.append(Argument(v))
        builder = CommandBuilder(facilities, {})
        cmd_instance = builder.make_cmd(cmd_class, [], opts, args, (0, 0), app._schema_module)
        cmd_instance.set_facility(facilities)
        var_storage = VarStorage(None, None)
        cmd_instance.set_var_storage(var_storage)
        executor = TransactionPendingAdaptor(CommandExecutor(cmd_instance, app, facilities), facilities)
        r = executor(None)
        return r

class TypeQuery(object):
    type = u'type'
    def __init__(self, label, value):
        self.label = label
        self.value = value
        self.optional = False
        self.repeat = False

class TagQuery(object):
    type = u'tag'
    def __init__(self, tag, value):
        self.tag = tag
        self.value = value
        self.label = None
        self.optional = False
        self.repeat = False

class ObjectQuery(object):
    type = u'object'
    def __init__(self, queries, wildcard):
        self.queries = queries
        self.wildcard = wildcard
        self.label = None
        self.optional = False
        self.repeat = False

class ArrayQuery(object):
    type = u'array'
    def __init__(self, queries, repeat):
        self.queries = queries
        self.repeat = repeat
        self.label = None
        self.optional = False

class AddressQuery(object):
    type = u'address'
    def __init__(self):
        self.value = None
        self.label = None
        self.optional = False
        self.repeat = False
