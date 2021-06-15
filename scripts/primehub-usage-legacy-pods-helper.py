import datetime
import json
import logging
import os
import sys
import time
from decimal import Decimal

import kubernetes
from dateutil.tz import tzutc
from kubernetes import client, watch
from kubernetes.client import V1Pod, ApiClient
from kubernetes.utils import parse_quantity
from urllib3.exceptions import ReadTimeoutError

from usage import logger, load_kubernetes_config
from usage.model import session_scope, Usage

PRIMEHUB_USAGE_ANNOTATION = 'primehub.io/usage'


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
    usage_annotation = metadata.annotations.get(PRIMEHUB_USAGE_ANNOTATION, None)
    if usage_annotation is None:
        return None
    return json.loads(usage_annotation)


class CRDObject(object):

    def __init__(self, object):
        self.object = object
        self.name = object['metadata']['name']
        self.group_name = object['spec']['groupName']
        self.user_name = object['spec']['userName']
        if self.object['kind'] == 'PhJob':
            self.instance_type = object['spec']['instanceType']
        if self.object['kind'] == 'PhDeployment':
            self.instance_type = object['spec']['predictors'][0]['instanceType']


def list_crd_objects(namespace, crd_type):
    api_instance = kubernetes.client.CustomObjectsApi(ApiClient())
    result = api_instance.list_namespaced_custom_object('primehub.io', 'v1alpha1', namespace, crd_type)
    output = dict()
    for x in result['items']:
        output[x['metadata']['uid']] = CRDObject(x)
    return output


def patch_op(path_template, value):
    ops = [dict(op="add",
                path=path_template % (PRIMEHUB_USAGE_ANNOTATION.replace("/", "~1")),
                value=json.dumps(value))]
    return json.dumps(ops)


def patch_pod_command(name, value):
    return """kubectl -n hub patch pod %s --type='json' -p '%s'""" % (name, patch_op("/metadata/annotations/%s", value))


def patch_deployment_command(name, value):
    return """kubectl -n hub patch deployment %s --type='json' -p '%s'""" \
           % (name, patch_op("/spec/template/metadata/annotations/%s", value))


def generate_scripts(namespace):
    load_kubernetes_config()
    v1 = client.CoreV1Api()

    phjobs = list_crd_objects(namespace, 'phjobs')
    for pod in v1.list_pod_for_all_namespaces(watch=False).items:
        if pod.metadata.labels is None:
            continue

        usage = get_usage_annotation(namespace, pod)
        generate_job_patch_command(phjobs, usage, pod)
        generate_jupyter_patch_command(usage, pod)

    app_v1 = client.AppsV1Api()
    phdeployments = list_crd_objects(namespace, 'phdeployments')
    for d in app_v1.list_namespaced_deployment(namespace, watch=False).items:
        if d.metadata.owner_references:
            owner = d.metadata.owner_references[0]
            if owner.kind != 'PhDeployment':
                continue

            usage = get_usage_annotation(namespace, d.spec.template)
            if usage is not None:
                continue

            ph_deploy = phdeployments[owner.uid]
            annotation = dict(component="deployment",
                              component_name=ph_deploy.name,
                              group=ph_deploy.group_name,
                              user=ph_deploy.user_name,
                              instance_type=ph_deploy.instance_type)

            print("# patch phdeployment deployment: %s, it might restart pods if anything have changed"
                  % ph_deploy.name)
            print(patch_deployment_command(ph_deploy.name, annotation))
            print("")


def generate_jupyter_patch_command(usage, pod):
    # generate patch for jupyter
    component = pod.metadata.labels.get('component', None)
    if component == 'singleuser-server':
        if usage is None:
            auditing = pod.metadata.annotations
            annotation = dict(component="jupyter",
                              component_name=pod.metadata.name,
                              group=auditing['auditing.launch_group_name'],
                              user=auditing['auditing.user_name'],
                              instance_type=auditing['auditing.instance_type'])
            print("# patch jupyter pod: %s" % pod.metadata.name)
            print(patch_pod_command(pod.metadata.name, annotation))
            print("")


def generate_job_patch_command(phjobs, usage, pod):
    # generate patch for phjob
    if pod.metadata.name.startswith('job-') and usage is None:
        # it is managed by PhJob
        if pod.metadata.owner_references:
            ref = pod.metadata.owner_references[0]
            if ref.kind == 'PhJob':
                job = phjobs[ref.uid]
                annotation = dict(component="job",
                                  component_name=job.name,
                                  group=job.group_name,
                                  user=job.user_name,
                                  instance_type=job.instance_type)
                print("# patch phjob pod: %s" % job.name)
                print(patch_pod_command(job.name, annotation))
                print("")


def main():
    namespace = os.environ.get('PRIMEHUB_USAGE_WATCHED_NAMESPACE', None)
    if namespace is None:
        logger.error('env PRIMEHUB_USAGE_WATCHED_NAMESPACE is required')
        sys.exit(1)
    generate_scripts(namespace)


if __name__ == '__main__':
    logger.setLevel(logging.ERROR)
    main()
