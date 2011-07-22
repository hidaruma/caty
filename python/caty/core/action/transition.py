from caty.core.exception import *
TRANSITION_DEF_ERROR = u'TRANSITION_DEF_ERROR'
class AnnotationInterpreter(object):
    def __init__(self, app):
        self._app = app

    def check(self, typeobj):
        raise NotImplementedError()

def Trigger(AnnotationInterpreter):
    def check(self, typeobj):
        if 'trigger' not in typeobj.annotations: return
        schemata = _schema_module.schema_finder.start()
        trigger_type = schemata['Trigger']
        if not trigger_type > typeobj:
            throw_caty_exception(
                TRANSITION_DEF_ERROR,
                '$name is not Trigger type',
                name=typeobj.name
            )


