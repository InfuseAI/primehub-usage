import datetime
from contextlib import contextmanager
from decimal import Decimal

from dateutil.tz import tzutc
from sqlalchemy import Column, Integer, Unicode, DECIMAL, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import threading

from usage import format_value, utc_now

Base = declarative_base()
_engine = None
_lock = threading.Lock()


class Usage(Base):
    __tablename__ = 'primehub_usages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(Unicode(36), nullable=False, index=True)
    pod_name = Column(Unicode(63), nullable=False)
    group_name = Column(Unicode(63), nullable=False)
    user_name = Column(Unicode(63), default="", nullable=False)
    component = Column(Unicode(63), default="", nullable=False)
    component_name = Column(Unicode(63), default="", nullable=False)
    instance_type = Column(Unicode(63), default="", nullable=False)
    gpu = Column(DECIMAL, nullable=False)
    cpu = Column(DECIMAL, nullable=False)
    memory = Column(DECIMAL, nullable=False)
    updated_time = Column(TIMESTAMP, nullable=False, index=True, default=func.now())
    scheduled_time = Column(TIMESTAMP, index=True)
    finished_time = Column(TIMESTAMP, index=True)

    def poke_updated_time(self):
        self.updated_time = utc_now()


class RunningPod(Base):
    __tablename__ = 'primehub_running_pods'
    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(Unicode(36), nullable=False, index=True)
    scheduled_time = Column(TIMESTAMP, index=True)
    updated_time = Column(TIMESTAMP, nullable=False, index=True, default=func.now())

    def poke_updated_time(self):
        self.updated_time = utc_now()


class MonthlyReport(Base):
    __tablename__ = 'primehub_monthly_report'
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_month = Column(Unicode(8), nullable=False, index=True)
    group_name = Column(Unicode(63), nullable=False)
    user_name = Column(Unicode(63), default="", nullable=False)
    component = Column(Unicode(63), default="", nullable=False)
    gpu_core_hours = Column(DECIMAL, nullable=False)
    cpu_core_hours = Column(DECIMAL, nullable=False)
    gb_memory_hours = Column(DECIMAL, nullable=False)
    usage_hours = Column(DECIMAL, nullable=False)
    running = Column(Unicode(1), nullable=False)

    @staticmethod
    def get_columns():
        return [x for x in MonthlyReport.__table__.columns.keys() if x != 'id']

    @staticmethod
    def get_csv_headers():
        columns = []
        for c in MonthlyReport.get_columns():
            # Add alias here
            if c == 'group_name':
                columns.append('group')
                continue
            if c == 'user_name':
                columns.append('user')
                continue
            columns.append(c)
        return ",".join(columns)

    def to_csv_entry(self):
        row = [format_value(getattr(self, x)) for x in MonthlyReport.get_columns()]
        return ",".join(row)

    def to_dict(self):
        d = {}
        for x in MonthlyReport.get_columns():
            d[x] = self.fmt(getattr(self, x))
        return d


@contextmanager
def session_scope(db_connection):
    get_engine(db_connection)
    session = sessionmaker(_engine)()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def get_engine(db_connection):
    global _engine
    with _lock:
        if _engine is None:
            _engine = create_engine(db_connection)
            Base.metadata.create_all(_engine)
    return _engine


if __name__ == '__main__':
    with session_scope('sqlite://') as s:
        print(s)
