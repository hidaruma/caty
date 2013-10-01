#coding: utf-8
import caty
from caty.core.command import Builtin
import caty.jsontools.selector as selector
import caty.jsontools as json
from caty.core.exception import throw_caty_exception

class Merge(Builtin):
    def setup(self, tree_name):
        self.tree_name = tree_name

    def execute(self, record):
        ts = self.arg0.get(self.tree_name)
        rectype = ts['nodeSet']
        k = self.defined_module.get_type(rectype).annotations['__identified'].value[2:] #XXX: 手抜き
        id = record[k]
        rel = None
        for n in ts['nodes']:
            if n['id'] == id:
                rel = n
                break
        else:
            throw_caty_exception(u'RecordNotFound', u'id=$id', id=id)
        record['parent'] = rel['parent']
        if rel['parent'] is not None:
            p = None
            for n in ts['nodes']:
                if n['id'] == rel['parent']:
                    record['position'] = n['childNodes'].index(id)
                    break
        return record
        

class Extract(Builtin):
    def execute(self, record):
        del record['parent']
        del record['childNodes']
        return record

