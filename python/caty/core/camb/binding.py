from caty.core.exception import throw_caty_exception
class ModuleBinderContainer(object):
    def __init__(self):
        self.binders = []

    def add_binder(self, binder):
        self.binders.append(binder)
        binder.parent = self

    def resolve(self, schema_module, dispatcher):
        pass

class ModuleBinder(object):
    def __init__(self, name, docstr):
        self.name= name
        self.bindings = []
        self.docstr = docstr

    def add_binding(self, binding):
        for binder in self.parent.binders:
            for b in binder.bindings:
                if b.port == binding.port:
                    throw_caty_exception(
                        u'CAMB_COMPILE_ERROR',
                        u'Binding `$name` is already defined in module $camb',
                        name=b.port, camb=binder.name)
        self.bindings.append(binding)

    def resolve(self, schema_module, dispatcher):
        pass

class Binding(object):
    def __init__(self, port, target, type):
        self.port = port
        self.target = target
        self.type= type
