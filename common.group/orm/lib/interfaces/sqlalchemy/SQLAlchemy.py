from caty.core.spectypes import UNDEFINED
from caty.core.facility import Facility, AccessManager


class SQLAlchemyBase(Facility):
    am = AccessManager()
    @am.update
    def create_table(self, table_class):
        return _create_table(table_class)

    def _create_table(self, table_class):
        raise NotImplementedError(u"_SQLAlchemy.create_table")

    @am.update
    def generate_py_class(self, name, type_object):
        return _generate_py_class(name, type_object)

    def _generate_py_class(self, name, type_object):
        raise NotImplementedError(u"_SQLAlchemy.generate_py_class")
