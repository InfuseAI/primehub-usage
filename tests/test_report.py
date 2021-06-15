import datetime
import logging
import time
import unittest

from dateutil.tz import tzutc
from sqlalchemy.orm import sessionmaker

from usage.model import session_scope, Usage, get_engine, MonthlyReport
from usage.report import generate_reports, generate_report, create_report_working_table

db_connection = 'postgresql://postgres:mysecretpassword@localhost:5432/postgres'


def is_local_database_available():
    try:
        with session_scope(db_connection) as s:
            result = s.bind.execute('SELECT version()').fetchall()
            for row in result:
                return True
    except Exception:
        return False


def create_test_data():
    u = Usage()
    u.uid = 'i-am-a-test-data'
    u.pod_name = 'i-am-a-test-data'
    u.group_name = 'test'
    u.user_name = 'test'
    u.component = 'jupyter'
    u.component_name = 'foo-bar'
    u.instance_type = 'cpu-1'
    u.gpu = 0
    u.cpu = 1
    u.memory = 1024 ** 3
    u.poke_updated_time()
    u.scheduled_time = datetime.datetime(1999, 2, 23, 18, 00, 00, tzinfo=tzutc())
    u.finished_time = datetime.datetime(1999, 4, 3, 17, 00, 00, tzinfo=tzutc())
    return u


class TestReport(unittest.TestCase):

    def setUp(self) -> None:
        if not is_local_database_available():
            self.skipTest('Skip regression tests, because localhost:5432/postgres is not available')

        with session_scope(db_connection) as s:
            data = create_test_data()
            s.add(data)
            self.usage = data

    def tearDown(self) -> None:
        if is_local_database_available():
            with session_scope(db_connection) as s:
                s.delete(self.usage)

    def test_usage_cross_months(self):
        # logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        with session_scope(db_connection) as s:
            generate_report(s,
                            datetime.datetime(1999, 2, 1, 00, 00, 00, tzinfo=tzutc()),
                            datetime.datetime(1999, 3, 1, 00, 00, 00, tzinfo=tzutc()))

            generate_report(s,
                            datetime.datetime(1999, 3, 1, 00, 00, 00, tzinfo=tzutc()),
                            datetime.datetime(1999, 4, 1, 00, 00, 00, tzinfo=tzutc()))

            generate_report(s,
                            datetime.datetime(1999, 4, 1, 00, 00, 00, tzinfo=tzutc()),
                            datetime.datetime(1999, 5, 1, 00, 00, 00, tzinfo=tzutc()))

            reports = [x for x in s.query(MonthlyReport).all() if x.report_month.startswith('1999')]

            # verify it breaks into 3 report month
            self.assertEqual(3, len(reports))

            def used_seconds(report_month, reports):
                v = [x for x in reports if x.report_month == report_month][0]
                s = int(v.usage_hours * 60 * 60)
                print('report {} used {} seconds (hours: {})'.format(report_month, s, v.usage_hours))
                return s

            def range_in_seconds(d1, d2):
                return abs((d1 - d2).total_seconds())

            # verify 1999/02 from 2/23 18:00 to 3/1 00:00
            self.assertEqual(range_in_seconds(
                datetime.datetime(1999, 2, 23, 18, 00, 00, tzinfo=tzutc()),
                datetime.datetime(1999, 3, 1, 00, 00, 00, tzinfo=tzutc())
            ), used_seconds('199902', reports))

            # verify 1999/03 from 3/1 00:00 to 4/1 00:00
            self.assertEqual(range_in_seconds(
                datetime.datetime(1999, 3, 1, 00, 00, 00, tzinfo=tzutc()),
                datetime.datetime(1999, 4, 1, 00, 00, 00, tzinfo=tzutc())
            ), used_seconds('199903', reports))

            # verify 1999/04 from 4/1 00:00 to 4/3 17:00
            self.assertEqual(range_in_seconds(
                datetime.datetime(1999, 4, 1, 00, 00, 00, tzinfo=tzutc()),
                datetime.datetime(1999, 4, 3, 17, 00, 00, tzinfo=tzutc())
            ), used_seconds('199904', reports))
