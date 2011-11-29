class ModuleBindings(object):
    def __init__(self, name, bindings, docstr):
        self.name= name
        self.bindings = bindings
        self.docstr = docstr

class Binding(object):
    def __init__(self, port, target, type):
        self.port = port
        self.target = target
        self.type= type
