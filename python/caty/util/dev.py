import traceback
def debug(*args):
    print u'(debug)',
    for a in args:
        print a,
    st = traceback.extract_stack()
    print '   ', st[-2][0], st[-2][1]
    print
