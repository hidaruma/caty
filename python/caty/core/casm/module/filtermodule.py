#coding: utf-8
from caty.core.casm.module.basemodule import *

class FilterModule(Module):
    def __init__(self, system):
        filterapp = system.dummy_app
        filterapp._name = u'filter'
        Module.__init__(self, filterapp)

