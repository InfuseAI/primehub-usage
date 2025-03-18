import datetime
import json
import time
from decimal import Decimal

from dateutil.tz import tzutc
from kubernetes import client, watch
from kubernetes.client import V1Pod
from kubernetes.utils import parse_quantity
from urllib3.exceptions import ReadTimeoutError

from usage import logger, load_kubernetes_config, utc_now
from usage.model import session_scope, Usage

EVENT_REQUEST_TIMEOUT = 60 * 10

# Let watcher save events to review and debug
save_events_to_file = False


def get_usage_annotation(namespace, pod):
    metadata = pod.metadata
    if metadata.namespace != namespace:
        return None

    if metadata.annotations is None or not metadata.annotations:
        return None

    """
    The data would like this:
    primehub.io/usage: '{"instance_type": "cpu-1", "component": "jupyter", "component_name": "jupyter-phadmin", "group": "phusers", "user": "phadmin"}'
    """
    return _parse_usage_annotation(metadata)


def _parse_usage_annotation(metadata):
    usage_annotation = metadata.annotations.get('primehub.io/usage', None)
    if usage_annotation is None:
        return None
    return json.loads(usage_annotation)

def _get_gpu_request(requests):
    if 'nvidia.com/gpu' in requests:
        return requests.get('nvidia.com/gpu')
    if 'amd.com/gpu' in requests:
        return requests.get('amd.com/gpu')
    for k, v in requests.items():
        if k.startswith('gpu.intel.com/'):
            return v
    return 0

def get_resources(pod):
    cpu = sum([parse_quantity(x.resources.to_dict().get("requests")['cpu']) for x in pod.spec.containers])
    memory = sum(
        [parse_quantity(x.resources.to_dict().get("requests")['memory']) for x in pod.spec.containers])
    gpu = sum([parse_quantity(_get_gpu_request(x.resources.to_dict().get("requests"))) for x in
               pod.spec.containers])
    return gpu, cpu, memory


def get_usage_times(pod: V1Pod):
    conditions = [x for x in pod.status.conditions if x.type == 'PodScheduled']
    scheduled = None
    finished = None
    if conditions:
        scheduled = conditions[0].last_transition_time

    if not pod.status.container_statuses:
        return scheduled, finished

    has_running_containers = [x for x in pod.status.container_statuses if x.state.running]
    if not has_running_containers:
        terminated_containers = [x.state.terminated.finished_at for x in pod.status.container_statuses if
                                 x.state.terminated if x.state.terminated]
        if terminated_containers:
            try:
                finished = max(terminated_containers)
            except TypeError:
                logger.warning('Error to parse finished-time => {}'.format(pod))

    return scheduled, finished


def save_events(event):
    if not save_events_to_file:
        return

    pod = event['object']
    raw_obj = event['raw_object']
    event_type = event['type']

    with open("{}-{}-{}-{}.json".format(int(time.time() * 100), pod.metadata.name, pod.metadata.uid, event_type),
              "w") as f:
        f.write(json.dumps(raw_obj, sort_keys=True, indent=2, separators=(',', ': ')))


def watch_events(namespace, db_connection):
    while True:
        try:
            _watch_events(namespace, db_connection)
        except ReadTimeoutError:
            logger.info('restart watcher after timelimit [ {} secs ] hit'.format(EVENT_REQUEST_TIMEOUT))
            continue


def _watch_events(namespace, db_connection):
    load_kubernetes_config()
    w = watch.Watch()
    v1 = client.CoreV1Api()
    for event in w.stream(v1.list_pod_for_all_namespaces, _request_timeout=EVENT_REQUEST_TIMEOUT):
        pod = event['object']
        event_type = event['type']

        save_events(event)

        usage = get_usage_annotation(namespace, pod)
        if usage is None:
            continue

        # the pod has not scheduled yet
        if pod.status.conditions is None:
            continue

        logger.info('{} {} {}'.format(event_type, pod.metadata.uid, pod.metadata.name))
        uid = pod.metadata.uid

        with session_scope(db_connection) as s:
            u = s.query(Usage).filter_by(uid=uid).one_or_none()
            if u is None:
                u = Usage()
                u.uid = uid
                u.pod_name = pod.metadata.name
                u.group_name = usage['group']
                u.user_name = usage.get('user', '')
                u.component = usage['component']
                u.component_name = usage['component_name']
                u.instance_type = usage['instance_type']

                gpu, cpu, memory = get_resources(pod)
                u.gpu = gpu
                u.cpu = cpu
                u.memory = memory

            u.poke_updated_time()
            u.scheduled_time, u.finished_time = get_usage_times(pod)
            # the deleted event might not have finished-time yet
            if u.finished_time is None and event_type == 'DELETED':
                u.finished_time = utc_now()
                logger.warning(
                    'patch finished-time by updated-time => {} {}'.format(pod.metadata.uid, pod.metadata.name))
            s.add(u)


if __name__ == '__main__':
    # save_events_to_file = True
    db_connection = 'postgresql://postgres:mysecretpassword@localhost:5432/postgres'
    # db_connection = 'sqlite://'
    watch_events('hub', db_connection)
