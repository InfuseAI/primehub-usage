import datetime
import json
import os
import unittest

from dateutil.tz import tzutc
from kubernetes import watch
from kubernetes.client import V1Pod, V1ObjectMeta, V1PodSpec, V1Container, V1ResourceRequirements

from usage import watcher
from usage.watcher import get_usage_annotation, get_resources, get_usage_times


def load_text(filename):
    with open(os.path.join(os.path.dirname(__file__), filename), 'r') as f:
        return f.read()


def make_pod_from_sample(pod_json):
    w = watch.Watch()
    return w.unmarshal_event(json.dumps(dict(object=json.loads(pod_json))), 'V1Pod')['object']


def make_pod(namespace):
    metadata = V1ObjectMeta()
    metadata.namespace = namespace
    metadata.annotations = dict()
    pod = V1Pod(api_version='v1', kind='Pod', metadata=metadata, spec=V1PodSpec(containers=[]))
    return pod


class TestWatcher(unittest.TestCase):

    def test_get_usage_annotation(self):
        pod = make_pod('primehub-ns')
        pod.metadata.annotations['primehub.io/usage'] \
            = '{"instance_type": "cpu-1", "component": "jupyter", "group":"phusers", "user": "phadmin", "component_name": "foobarbar"}'

        u = get_usage_annotation('primehub-ns', pod)
        self.assertEqual(u['instance_type'], 'cpu-1')
        self.assertEqual(u['component'], 'jupyter')
        self.assertEqual(u['component_name'], 'foobarbar')
        self.assertEqual(u['group'], 'phusers')
        self.assertEqual(u['user'], 'phadmin')

    def test_get_resources(self):
        pod = make_pod('primehub-ns')
        requests = dict(cpu='1500m', memory='1Gi')
        requests['nvidia.com/gpu'] = '4'
        pod.spec.containers = [V1Container(name='foo', resources=V1ResourceRequirements(requests=requests))]
        gpu, cpu, memory = get_resources(pod)

        from decimal import Decimal
        self.assertEqual(Decimal(4), gpu)
        self.assertEqual(Decimal(1.5), cpu)
        self.assertEqual(Decimal(1 * 1024 ** 3), memory)

    def test_parse_time_for_normal_completed_pod(self):
        scheduled_time, finished_time = get_usage_times(
            make_pod_from_sample(load_text('001_normal_completed_pod.json')))

        self.assertEqual(datetime.datetime(2020, 7, 22, 4, 51, 22, tzinfo=tzutc()), scheduled_time)
        self.assertEqual(datetime.datetime(2020, 7, 22, 4, 56, 16, tzinfo=tzutc()), finished_time)
