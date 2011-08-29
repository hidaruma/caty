#coding: utf-8
import caty.jsontools as json
import caty.core.runtimeobject as ro
class InternalException(Exception):
    def __init__(self, msg, **kwds):
        Exception.__init__(self, ro.i18n.get(msg, **kwds))

class CatyException(Exception):
    u"""Caty 例外。詳細は specdocs 参照
    """
    def __init__(self, error_tag, message, error_class=None, error_id=None, stack_trace=None, place_holder={}, **kwds):
        o = {}
        o['message'] = message if isinstance(message, unicode) else unicode(message)
        if error_class:
            o['class'] = error_class
        if error_id:
            o['id'] = error_id
        if stack_trace:
            o['stackTrace'] = stack_trace
        for k, v in place_holder.items():
            o[k] = v
        for k, v in kwds.items():
            o[k] = v
        self.__json_obj = json.tagged(error_tag, o)
        self.__place_holder = place_holder if place_holder else kwds
        # self.__json_obj.update(place_holder)
        self.__message = message
        Exception.__init__(self, self.tag + ': ' + ro.i18n.get(message, place_holder, **kwds))

    @property
    def tag(self):
        return json.tag(self.__json_obj)

    @property
    def error_obj(self):
        return json.untagged(self.__json_obj)

    def to_json(self):
        return self.__json_obj

    def get_message(self, i18n):
        return i18n.get(self.__message, self.__place_holder)

    def __unicode__(self):
        return self.__message.safe_substitute(self.__place_holder)
    message = property(__unicode__)

def throw_caty_exception(tag, message, error_class=None, error_id=None, stack_trace=None, **kwds):
    raise CatyException(tag, message, error_class, error_id, stack_trace, **kwds)

class SubCatyException(CatyException):
    def __init__(self, **kwds):
        CatyException.__init__(self, self.error_type, self.error_message, **kwds)

class FileNotFound(SubCatyException):
    error_type = 'FileNotFound'
    error_message = u'File does not exists: $path'


class FileIOError(SubCatyException):
    error_type = 'FileIOError'
    error_message = u'Failed to read file: $path'

class UnableToAccess(SubCatyException):
    error_type = 'UnableToAccess'
    error_message = u'Can not access to $path'

