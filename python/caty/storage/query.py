from caty.jsontools import TaggedValue, TagOnly
def not_null(): return TagOnly('_NOT_NULL')
def any_(): return TagOnly('_ANY')
def or_(*v): return TaggedValue('_OR', v)
def and_(*v): return TaggedValue('_AND', v)
def like(v): return TaggedValue('_LIKE', v)
def contains(v): return TaggedValue('_CONTAINS', v)
def each(v): return TaggedValue('_EACH', v)
def lt(v): return TaggedValue('_LT', v)
def le(v): return TaggedValue('_LE', v)
def gt(v): return TaggedValue('_GT', v)
def ge(v): return TaggedValue('_GE', v)
def between(v1, v2): return TaggedValue('_BETWEEN', (v1, v2))

