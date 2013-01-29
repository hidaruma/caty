from caty.core.facility import Facility, READ
try:
    from sqlalchemy import *
    from sqlalchemy.orm import *
except:
    print '[Warning] sqlalchemy is required'
else:
    class SQLAlchemyWrapper(Facility):
        config = None

        @classmethod
        def initialize(cls, app_instance, config):
            if not config:
                config = {}
            cls.config = config
            cfg = {'encoding': 'utf-8'}
            url = 'sqlite:///:memory:'
            for k, v in config.items():
                if k == 'url':
                    url = v
                else:
                    cfg[k] = v
            cls.engine = create_engine(url, **cfg)

        @classmethod
        def instance(cls, app, system_param):
            return SQLAlchemyWrapper(system_param)

        @classmethod
        def finalize(cls, app):
            pass

        def create(self, mode, user_param=None):
            obj = Facility.create(self, mode)
            return obj

        def clone(self):
            return self

        def __init__(self, *ignore):
            conn = self.engine.connect()
            self.conn = conn
            SessionClass = session_maker(bind==conn, autoflush=True)
            SessionClass.configure(bind=conn)
            self.session = SessionClass()

        def commit(self):
            try:
                self.session.comit()
            finally:
                self.conn.close()

        def cancel(self):
            try:
                self.session.rollback()
            finally:
                self.conn.close()
