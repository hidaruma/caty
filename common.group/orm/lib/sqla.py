#coding: utf-8
from caty.core.typeinterface import dereference
try:
    from sqlalchemy import *
    from sqlalchemy.orm import *
    from interfaces.sqlalchemy.SQLAlchemy import SQLAlchemyBase
except:
    import traceback
    traceback.print_exc()
    print '[Warning] sqlalchemy is not installed or sqlalchemy IDL is not compiled'
else:
    class SQLAlchemyWrapper(SQLAlchemyBase):
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
            SessionClass = sessionmaker(bind=conn, autoflush=True)
            SessionClass.configure(bind=conn)
            self.session = SessionClass()

        def commit(self):
            try:
                self.session.commit()
            finally:
                self.conn.close()

        def cancel(self):
            try:
                self.session.rollback()
            finally:
                self.conn.close()

        def _generate_py_class(self, object_type, name):
            buff = []
            _ = buff.append
            _(u'from sqlalchemy.ext.declarative import declarative_base')
            _(u'from sqlalchemy import *')
            _(u'from sqlalchemy.orm import *')
            _(u'from string import Template')
            _(u'from caty.util.collection import conditional_dict')
            _(u'Base = declarative_base()')
            _(u'class %s(Base):' % name)
            _(u'    __tablename__ = "%s"' % name)
            # optionalなプロパティの初期値はNoneになるが、これは型エラーを引き起こす。
            # DBにおいてnullableなプロパティを記録しておき、JSON変換時に適宜undefinedにする。
            _(u'    __nullable__ = set()')
            for k, v in object_type.items():
                if v.optional:
                    _(u'    __nullable__.add("%s")' % k)
            for k, v in object_type.items():
                nullable = 'False'
                primary_key = 'False'
                if v.optional:
                    v = dereference(v, reduce_option=True)
                    nullable = 'True'
                if 'primary-key' in v.annotations:
                    primary_key = 'True'
                if v.type == 'string':
                    t = 'String'
                elif v.type == 'integer':
                    t = 'Integer'
                elif v.type == 'number':
                    t = 'Numeric'
                else:
                    throw_caty_exception(u'NotImplemented', v.type)
                _("    %s = Column('%s', %s, primary_key=%s, nullable=%s)" % (k, k, t, primary_key, nullable))
            init = []
            __ = init.append
            __(u'    def __init__(self')
            __(u',')
            for k, v in object_type.items():
                if not v.optional:
                    __(u'%s' % k)
                    __(u',')
            for k, v in object_type.items():
                if v.optional:
                    v = dereference(v, reduce_option=True)
                    if 'default' not in v.annotations:
                        __(u'%s=None' % (k))
                    else:
                        __(u'%s=%s' % (k, v.annotations['default'].value))
                    __(u',')
            init.pop(-1)
            __('):')
            _(u''.join(init))
            for k, v in object_type.items():
                _('        self.%s = %s' % (k, k))
            _(u'')
            rep = []
            __ = rep.append
            _(u'    def __repr__(self):')
            num = 0
            for k, v in object_type.items():
                __(u"'{%d}'" % num)
                __(u', ')
                num += 1
            rep.pop(-1)
            fmt = ''.join(rep)
            rep[:] = []
            __(u'       return Template("%s<%s>")' % (name, fmt))
            __(u'.substitute((')
            for k, v in object_type.items():
                __("self.%s" % k)
                __(', ')
            rep.pop(-1)
            __(u'))')
            _(u''.join(rep))
            _(u'')
            _(u'    def to_json(self):')
            _(u'        return conditional_dict(lambda k, v: not(v is None and k in self.__nullable__), {')
            for k, v in object_type.items():
                _('            "%s": self.%s,' % (k, k))
            _(u'        })')
            return u'\n'.join(buff)

        def _create_table(self, cls):
            cls.metadata.create_all(self.engine)
        

