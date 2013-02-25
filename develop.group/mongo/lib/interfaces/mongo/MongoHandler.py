from caty.core.spectypes import UNDEFINED
from caty.core.facility import Facility, AccessManager


class MongoHandlerBase(Facility):
    am = AccessManager()