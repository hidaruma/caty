from caty.core.schema import types
locals().update(types)
def get_schema(name):
    return types[name]

