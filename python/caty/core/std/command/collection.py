from caty.core.facility import Facility, READ

class DefaultStorage(Facility):
    __db__ = {}
    def __init__(self, mode, system_param):
        Facility.__init__(self, mode)
        self.dbname = system_param
        if system_param not in DefaultStorage.__db__:
            DefaultStorage.__db__[system_param] = {}

    @classmethod
    def initialize(cls, app_instance, config):
        pass

    @classmethod
    def instance(cls, app, system_param):
        return DefaultStorage(READ, system_param)

    @classmethod
    def finalize(cls, app):
        pass

    def create(self, mode, user_param=u'default-collection'):
        obj = Facility.create(self, mode)
        obj.colname = user_param
        if user_param not in DefaultStorage.__db__[self.dbname]:
            DefaultStorage.__db__[self.dbname][user_param] = {}
        return obj

    def clone(self):
        return self

    @property
    def db(self):
        return DefaultStorage.__db__[self.dbname][self.colname]

