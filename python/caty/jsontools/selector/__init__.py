from caty.jsontools.selector.parser import JSONPathSelectorParser

def compile(pathexp, empty_when_error=False):
    return JSONPathSelectorParser(empty_when_error).run(pathexp)


