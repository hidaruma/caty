#coding: utf-8
import caty
from caty.core.command import Builtin
import caty.jsontools.selector as selector
import caty.jsontools as json
from caty.core.exception import throw_caty_exception
from caty.core.facility import DUAL

class Grouping(Builtin):
    def execute(self, gi):
        src_ent = self.current_app.get_entity(gi['src'])
        src = src_ent.create(DUAL)
        trg_ent = self.current_app.get_entity(gi['trg'])
        trg = trg_ent.create(DUAL)
        keys = gi['keys']
        cond = gi['cond']
        records = map(lambda k: [k, src.get(k)], keys)
        gid = gi['name']
        groups = self._make_groups(cond, records)
        grec = {u'name': gid, u'nodes': groups.values(), u'nodeSet': src_ent.module_name + ':' + gi['src']}
        if trg.exists(gid):
            trg.replace(gid, grec)
        else:
            trg.insert(gid, grec)
        return json.tagged(u'__r', {u't': trg_ent.module_name + ':' + gi['trg'], u'a': [gid]})

    def _make_groups(self, cond, records):
        groups = {}
        q = json.untagged(cond)
        if self._is_value_cond(cond):
            if isinstance(q, dict):
                path = q['field']
            else:
                path = q
            s = selector.compile(path)
            for i, r in records:
                try:
                    v = s.select(r).next()
                except:
                    v = u'None'
                key = u'__id_%s' % (json.pp(v).strip(u'"'))
                if key not in groups:
                    groups[key] = {
                        u'id': key,
                        u'parent': None,
                        u'childNodes': [[i, r]]
                    }
                else:
                    groups[key][u'childNodes'].append([i, r])
        elif self._is_range_cond(cond):
            path = q['field']
            s = selector.compile(path)
            orig = q.get(u'origin', 0)
            step = q['step']
            for i, r in records:
                try:
                    v = s.select(r).next()
                except:
                    v = 0
                if v < orig:
                    continue
                key = u'__id_%s' % (json.pp(v/step).strip(u'"'))
                if key not in groups:
                    groups[key] = {
                        u'id': key,
                        u'parent': None,
                        u'childNodes': [[i, r]]
                    }
                else:
                    groups[key][u'childNodes'].append([i, r])
        else:
            raise NotImplementedError()
        if isinstance(q, dict):
            mob = q.get(u'memberOrderBy')
            if mob:
                self._sort_groups(groups, mob)
            if q.get(u'groupOrderBy', u'+') == u'-':
                for v in groups.values():
                    v['childNodes'].reverse()

        for v in groups.values():
            v['childNodes'] = [c[0] for c in v['childNodes']]
        return groups

    def _is_value_cond(self, cond):
        return json.tag(cond) in (u'val', u'string')

    def _is_range_cond(self, cond):
        return json.tag(cond) == u'range'


    def _sort_groups(self, groups, mob):
        if not isinstance(mob, list):
            mob = [mob]
        func = _make_comparator(mob)
        for g in groups.values():
            g['childNodes'].sort(func)
        return groups

def _make_comparator(key):
    def cmp_obj(a, b):
        r = 0
        for k in key:
            asc = True
            path = selector.compile(k)
            r = cmp(path.select(a[1]).next(), path.select(b[1]).next())
            if r != 0:
                return r
        return r
    return cmp_obj

