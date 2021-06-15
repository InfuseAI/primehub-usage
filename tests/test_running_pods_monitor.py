import datetime
import logging
import time
import unittest

from dateutil.tz import tzutc
from sqlalchemy.orm import sessionmaker

from usage.model import session_scope, Usage, get_engine, MonthlyReport, RunningPod
from usage.report import generate_reports, generate_report, create_report_working_table
from usage.running_pods_monitor import update_finished_time, EVENT_REQUEST_TIMEOUT, \
    update_finished_time_for_no_event_pods

UNFINISHED_UID = 'i-am-a-unfinished-pod'
NO_USAGE_UID = 'event-existing-but-no-usage'

db_connection = 'postgresql://postgres:mysecretpassword@localhost:5432/postgres'


def is_local_database_available():
    try:
        with session_scope(db_connection) as s:
            result = s.bind.execute('SELECT version()').fetchall()
            for row in result:
                return True
    except Exception:
        return False


def create_test_data(uid=UNFINISHED_UID):
    u = Usage()
    u.uid = uid
    u.pod_name = 'i-am-a-unfinished-pod'
    u.group_name = 'test'
    u.user_name = 'test'
    u.component = 'jupyter'
    u.component_name = 'foo-bar'
    u.instance_type = 'cpu-1'
    u.gpu = 0
    u.cpu = 1
    u.memory = 1024 ** 3
    u.poke_updated_time()
    u.scheduled_time = datetime.datetime(2020, 1, 1, 18, 00, 00, tzinfo=tzutc())
    u.finished_time = None
    return u


def create_event(uid):
    event = RunningPod()
    event.uid = uid
    event.scheduled_time = datetime.datetime.utcnow()
    event.updated_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=EVENT_REQUEST_TIMEOUT)
    with session_scope(db_connection) as s:
        s.add(event)


class TestRunningPods(unittest.TestCase):

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

            with session_scope(db_connection) as s:
                self.running_pod_by_uid(s).delete()
                s.query(RunningPod).filter_by(uid=NO_USAGE_UID).delete()

    def test_running_pods_event_existing_without_usage_data(self):
        # there is an event in primehub_running_pods table without related usage
        create_event(NO_USAGE_UID)

        # invoke updater
        update_finished_time(db_connection)

        # verifying the event has gone
        self.verify_event_deleted(NO_USAGE_UID)

    def verify_event_deleted(self, uid):
        with session_scope(db_connection) as s:
            result = s.query(RunningPod).filter_by(uid=uid).one_or_none()
            self.assertIsNone(result)

    def test_unfinished_pods(self):
        # there is an unfinished pod in primehub_usages table
        # there is an event in primehub_running_pods table
        create_event(UNFINISHED_UID)

        # pre-condition
        # we found data both in usage and event
        with session_scope(db_connection) as s:
            self.assertIsNotNone(self.running_pod_by_uid(s).one())

            # before updating the finished_time is none
            usage = s.query(Usage).filter_by(uid=UNFINISHED_UID).one()
            self.assertIsNone(usage.finished_time)

        # invoke updater at the first round
        update_finished_time(db_connection)

        # verify usage marked finished
        with session_scope(db_connection) as s:
            self.assertIsNotNone(self.running_pod_by_uid(s).one())

            # before updating the finished_time is none
            usage = s.query(Usage).filter_by(uid=UNFINISHED_UID).one()
            self.assertIsNotNone(usage.finished_time)

        # invoke updater at the second round
        update_finished_time(db_connection)

        # verify usage still marked finished and event is deleted
        with session_scope(db_connection) as s:
            self.assertIsNone(self.running_pod_by_uid(s).one_or_none())

            # before updating the finished_time is none
            usage = s.query(Usage).filter_by(uid=UNFINISHED_UID).one()
            self.assertIsNotNone(usage.finished_time)

    def running_pod_by_uid(self, s):
        return s.query(RunningPod).filter_by(uid=UNFINISHED_UID)


UID_FOR_POD_WITHOUT_EVENTS = 'pod-without-event'


class TestEventsNotExistingInRunningPods(unittest.TestCase):

    def setUp(self) -> None:
        if not is_local_database_available():
            self.skipTest('Skip regression tests, because localhost:5432/postgres is not available')

    def tearDown(self) -> None:
        if is_local_database_available():
            with session_scope(db_connection) as s:
                s.query(Usage).filter_by(uid=UID_FOR_POD_WITHOUT_EVENTS).delete()

    def test_finished_pods_without_any_events(self):
        # there is an unfinished pod in primehub_usages table
        # there is no events in primehub_running_pods table

        with session_scope(db_connection) as s:
            s.add(create_test_data(uid=UID_FOR_POD_WITHOUT_EVENTS))

        # verify the pod has not finished yet
        with session_scope(db_connection) as s:
            self.assertIsNone(s.query(Usage).filter_by(uid=UID_FOR_POD_WITHOUT_EVENTS).one().finished_time)

        # patch the finished time in pods without events
        update_finished_time_for_no_event_pods(db_connection)

        # verify finished_time should be updated_time
        with session_scope(db_connection) as s:
            usage = s.query(Usage).filter_by(uid=UID_FOR_POD_WITHOUT_EVENTS).one()
            self.assertEqual(usage.updated_time, usage.finished_time)
