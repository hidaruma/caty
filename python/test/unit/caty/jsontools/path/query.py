# coding: utf-8
from caty.testutil import *
from caty.jsontools.path.query import *

def mk_query(s):
    return query.run(s)

class QueryTest(TestCase):
    def test_find(self):
        jo = ({'foo':'foo!!', 'bar': {'buz':'buz!!'}})
        query = mk_query('$.foo')
        v = list(query.find(jo))[0]
        self.assertEquals('foo!!', v)

        query = mk_query('$.bar.buz')
        v = list(query.find(jo))[0]
        self.assertEquals('buz!!', v)

    def test_find_list(self):
        jo = ({'foo':[1,2,3]})
        query = mk_query('$.foo.#')
        v = list(query.find(jo))
        self.assertEquals([1,2,3], v)

    def test_find_objmember(self):
        jo = ({'foo':{'a': 1, 'b': 2, 'c': 3}})
        query = mk_query('$.foo.*')
        v = list(sorted(query.find(jo)))
        self.assertEquals([1,2,3], v)

    def test_find_obj_root(self):
        jo = ({'foo':{'a': 1, 'b': 2, 'c': 3}})
        query = mk_query('$')
        v = query.find(jo).next()
        self.assertEquals(jo, v)


if __name__ == '__main__': 
    test(QueryTest)

