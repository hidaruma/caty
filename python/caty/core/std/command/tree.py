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
            record['parent'] = None
            return record
        record['parent'] = rel['parent']
        if rel['parent'] is not None:
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


class Update(Builtin):
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
            rel = self._insert(id, record, ts)
        prev_position = None
        if rel['parent'] is not None:
            p = None
            for n in ts['nodes']:
                if n['id'] == rel['parent']:
                    if id in n['childNodes']:
                        prev_position = n['childNodes'].index(id)
        if record.get('parent') is not None:
            if rel['parent'] == record['parent']:
                if record.get('position') is None or record['position'] == prev_position:
                    pass # 同じ親へのposition未指定の更新は何もしない
                else:
                    self._update_order(id, record, ts)
            else:
                rel['parent'] = record['parent']
                self._delete_node(id, ts)
                self._update_order(id, record, ts)
        else:
            if record.get('position') is None or record['position'] == prev_position:
                pass # 親がnullならposition未指定の更新は何もしない
            else:
                record['parent'] = rel['parent']
                self._update_order(id, record, ts) #親がnullかつposition指定時は兄弟位置の変更
                record['parent'] = None
        self.arg0.replace(self.tree_name, ts)
        return record

    def _insert(self, id, record, tree_structure):
        new_node = {u'parent': record.get('parent'), u'childNodes': [], u'id': id}
        tree_structure['nodes'].append(new_node)
        return new_node

    def _update_order(self, id, record, tree_structure):
        for n in tree_structure['nodes']:
            if n['id'] == record['parent']:
                if id in n['childNodes']:
                    n['childNodes'].remove(id)
                n['childNodes'].insert(record['position'], id)
                return
        if record['parent'] is not None:
            throw_caty_exception(u'RecordNotFound', u'id=$id', id=record['parent'])

    def _delete_node(self, id, tree_structure):
        to_del = None
        for n in tree_structure['nodes']:
            if id in n['childNodes']:
                n['childNodes'].remove(id)

class Delete(Builtin):
    def setup(self, tree_name=None):
        self.tree_name = tree_name

    def execute(self, record):
        if self.tree_name:
            tlist = [self.arg0.get(self.tree_name)]
        else:
            tlist = [self.arg0.all()]
        record['parent'] = None
        if 'position' in record:
            del record['position']
        for ts in tlist:
            rectype = ts['nodeSet']
            k = self.defined_module.get_type(rectype).annotations['__identified'].value[2:] #XXX: 手抜き
            id = record[k]
            self._delete_node(id, ts)
            self.arg0.replace(self.tree_name, ts)
        return record

    def _delete_node(self, id, tree_structure):
        to_del = None
        for n in tree_structure['nodes']:
            if id in n['childNodes']:
                n['childNodes'].remove(id)
            if id == n['id']:
                to_del = n
        for n in tree_structure['nodes']:
            for id in to_del['childNodes']:
                if id == n['id']:
                    n['parent'] = None
        tree_structure['nodes'].remove(to_del)


