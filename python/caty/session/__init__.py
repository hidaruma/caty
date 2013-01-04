#coding: utf-8
def initialize(obj):
    try:
        exec 'import %s as sessionimpl' % obj['module']
    except:
        import traceback
        traceback.print_exc()
        print '[Warning] No module named %s. Use caty.session.memory insted' % obj['module']
        import caty.session.memory as sessionimpl
    session = SessionMiddleWare(sessionimpl.SessionStorage(obj['conf']), sessionimpl.WSGISessionWrapper, obj['conf'])
    return session

class SessionMiddleWare(object):
    def __init__(self, storage, wrapper, conf):
        self.storage = storage
        self.wrapper = wrapper
        self.conf = conf

