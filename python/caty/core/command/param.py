from caty.jsontools import tagged
class Param(object): pass


class Option(Param):
    type = 'option'
    def __init__(self, key, value):
        self.key = key.lstrip('-')
        self.value = value

    def reify(self):
        return tagged(u'_opt', {'key': self.key, 'value': self.value})

class OptionLoader(Param):
    type = 'option_loader'
    def __init__(self, key, optional):
        self.key = key.lstrip('-')
        self.optional = optional

    def reify(self):
        return tagged(u'_optLoader', {'key': self.key, 'optional': self.optional})

class OptionVarLoader(Param):
    type = 'var'
    def __init__(self, key, value, optional, default):
        self.key = key.lstrip('-')
        self.value = value
        self.optional = optional
        self.default = default

    def reify(self):
        return tagged(u'_optVarLoader', {'key': self.key, 'value': self.value, 'optional': self.optional})

class GlobOption(Param):
    type = 'glob'
    def reify(self):
        return tagged(u'_glob', {})


class GlobArg(Param):
    type = 'glob'

    def reify(self):
        return tagged(u'_grag', {})


class Argument(Param):
    type = 'arg'
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return '[arg]' + repr(self.value)

    def reify(self):
        return tagged(u'_arg', {'value': self.value})

class NamedArg(Param):
    type = 'narg'
    def __init__(self, key, optional, default):
        self.key = key
        self.optional = optional
        self.default = default

    def __repr__(self):
        r = '[narg]' + repr(self.key)
        if self.optional:
            return r+'?'
        else:
            return r

    def reify(self):
        return tagged(u'_narg', {'key': self.key, 'optional': self.optional})

class IndexArg(Param):
    type = 'iarg'
    def __init__(self, index, optional, default):
        self.index = index
        self.optional = optional
        self.default = default

    def __repr__(self):
        r = '[iarg]' + repr(self.index)
        if self.optional:
            return r+'?'
        else:
            return r

    def reify(self):
        return tagged(u'_iarg', {'index': self.index, 'optional': self.optional})

