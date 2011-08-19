# coding: utf-8
from StringIO import StringIO

from caty.jsontools.path.query import query
from caty.jsontools.path.validator import validator
from caty.util.cache import memoize

def build_query(q):
    if not q.startswith('$.'):
        if q.startswith('.'):
            q = '$' + q
        else:
            q = '$.' + q
    finder = _build(q)
    finder.reset()
    return finder

@memoize
def _build(s):
    return query.run(s)


def build_validator(expression):
   return validator.run(expression)


