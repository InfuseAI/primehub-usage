import datetime
import json
import time
from decimal import Decimal
import logging

from dateutil.tz import tzutc
from kubernetes import client, config, watch
from kubernetes.client import V1Pod
from kubernetes.utils import parse_quantity
from urllib3.exceptions import ReadTimeoutError

from usage import logger, load_kubernetes_config
from usage.model import session_scope, Usage, RunningPod

EVENT_REQUEST_TIMEOUT = 30 * 10


def validate(namespace, pod):
    metadata = pod.metadata
    if metadata.namespace != namespace:
        return None

    if metadata.annotations is None or not metadata.annotations:
        return None

    usage_annotation = metadata.annotations.get('primehub.io/usage', None)
    return usage_annotation is not None


def get_scheduled_time(pod: V1Pod):
    conditions = [x.last_transition_time for x in pod.status.conditions if x.type == 'PodScheduled']
    if conditions:
        return conditions[0]
    return None


def update_time_for_events(namespace, db_connection):
    while True:
        try:
            update_finished_time_for_no_event_pods(db_connection)
            execute_update_time_for_events(namespace, db_connection)
        except ReadTimeoutError:
            logger.info('restart watcher after timelimit [ {} secs ] hit'.format(EVENT_REQUEST_TIMEOUT))

            # find unfinished pods and handle it
            try:
                update_finished_time(db_connection)
            except BaseException:
                pass

            # keep monitoring pods
            continue


def watch_pods(v1, w):
    return w.stream(v1.list_pod_for_all_namespaces, _request_timeout=EVENT_REQUEST_TIMEOUT)


def execute_update_time_for_events(namespace, db_connection):
    load_kubernetes_config()
    w = watch.Watch()
    v1 = client.CoreV1Api()

    for event in watch_pods(v1, w):
        pod = event['object']
        event_type = event['type']

        if not validate(namespace, pod):
            continue

        # the pod has not scheduled yet
        if pod.status.conditions is None:
            continue

        logger.info('{} {} {}'.format(event_type, pod.metadata.uid, pod.metadata.name))
        uid = pod.metadata.uid
        scheduled_time = get_scheduled_time(pod)

        if scheduled_time is None:
            continue

        with session_scope(db_connection) as s:
            o = s.query(RunningPod).filter_by(uid=uid).one_or_none()
            if o is not None:
                o.poke_updated_time()
                s.add(o)
            else:
                o = RunningPod()
                o.scheduled_time = scheduled_time
                o.uid = uid
                o.poke_updated_time()
                s.add(o)


def inactive_datetime(interval):
    return datetime.datetime.utcnow() - datetime.timedelta(seconds=interval)


def update_finished_time(db_connection):
    with session_scope(db_connection) as s:
        non_running_pods = s.query(RunningPod).filter(
            RunningPod.updated_time < inactive_datetime(EVENT_REQUEST_TIMEOUT))
        for event in non_running_pods:
            usage = s.query(Usage).filter_by(uid=event.uid).one_or_none()
            if usage is None:
                logger.warning('Cannot find the pod {} in the usage list'.format(event.uid))
                s.delete(event)
                continue

            # set finished_time to a unfinished pod at first round
            # remove a event from running pods at the next round
            if usage.finished_time is None:
                logger.warning('Mark as finished to pod {} {}'.format(usage.pod_name, usage.uid))
                usage.finished_time = event.updated_time
                s.add(usage)
            else:
                s.delete(event)


def update_finished_time_for_no_event_pods(db_connection):
    with session_scope(db_connection) as s:
        for usage in s.query(Usage).filter_by(finished_time=None).all():
            running_pod = s.query(RunningPod).filter_by(uid=usage.uid).one_or_none()
            if running_pod is None:
                usage.finished_time = usage.updated_time
                logger.warning(
                    'Cannot find the pod {} in the running pods! Patch finished_time by updated_time'.format(usage.uid))


if __name__ == '__main__':
    # save_events_to_file = True
    db_connection = 'postgresql://postgres:mysecretpassword@localhost:5432/postgres'
    # db_connection = 'sqlite://'

    EVENT_REQUEST_TIMEOUT = 10
    update_time_for_events('hub', db_connection)
