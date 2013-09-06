import sys, traceback
def debug(*args):
    try:
        print u'(debug)',
        for a in args:
            print a,
        st = traceback.extract_stack()
        print '   ', st[-2][0], st[-2][1]
        print
    except:
        traceback.print_exc()

def inject_tb(obj):
    import traceback, sys
    obj.traceback = ''.join(traceback.format_list(traceback.extract_stack(sys._getframe())))


