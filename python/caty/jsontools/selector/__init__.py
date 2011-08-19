from caty.jsontools.selector.parser import JSONPathSelectorParser

def compile(pathexp, empty_when_error=False):
    if not pathexp.startswith('$.'):
        if pathexp.startswith('.'):
           pathexp = '$' + pathexp
        else:
            pathexp = '$.' + pathexp
    return JSONPathSelectorParser(empty_when_error).run(pathexp)


