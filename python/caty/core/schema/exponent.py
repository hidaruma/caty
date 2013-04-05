from caty.core.schema.base import *

class ExponentSchema(SchemaBase, Exponent):
    def __init__(self, intype, outtype, argstype, optionstype):
        self._intype = intype
        self._outtype = outtype
        self._argstype = argstype
        self._optionstype = optionstype


        

