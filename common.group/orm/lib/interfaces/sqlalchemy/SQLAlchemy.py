from caty.core.spectypes import UNDEFINED
from caty.core.facility import Facility, AccessManager


class SQLAlchemyBase(Facility):
    am = AccessManager()
    @am.update
    def create_table(self, input):
        return self._create_table(input)

    def _create_table(self, input):
        raise NotImplementedError(u"SQLAlchemy._create_table")

    @am.update
    def generate_py_class(self, input, name):
        return self._generate_py_class(input, name)

    def _generate_py_class(self, input, name):
        raise NotImplementedError(u"SQLAlchemy._generate_py_class")
