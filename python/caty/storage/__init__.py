#coding: utf-8
from caty.storage import sqlite
from caty.util import memoize
from caty.jsontools import TagOnly
from caty.util.path import join
from caty.core.exception import InternalException

def initialize(config):
    m = config['module']
    exec 'import %s as storagemodule' % m
    return storagemodule.initialize(config['conf'])

