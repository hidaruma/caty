class Param(object):
    pass

class Option(Param):
    type = 'option'
    def __init__(self, key, value):
        self.key = key.lstrip('-')
        self.value = value

class OptionLoader(Param):
    type = 'option_loader'
    def __init__(self, key, optional):
        self.key = key.lstrip('-')
        self.optional = optional

class Argument(Param):
    type = 'arg'
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return '[arg]' + repr(self.value)

class NamedArg(Param):
    type = 'narg'
    def __init__(self, key, optional):
        self.key = key
        self.optional = optional

    def __repr__(self):
        r = '[narg]' + repr(self.key)
        if self.optional:
            return r+'?'
        else:
            return r

class IndexArg(Param):
    type = 'iarg'
    def __init__(self, index, optional):
        self.index = index
        self.optional = optional

    def __repr__(self):
        r = '[iarg]' + repr(self.index)
        if self.optional:
            return r+'?'
        else:
            return r
