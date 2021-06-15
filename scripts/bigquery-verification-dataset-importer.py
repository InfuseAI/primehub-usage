from google.cloud import bigquery
from sqlalchemy import Column, Integer, Unicode, DECIMAL, TIMESTAMP, func

from usage.model import session_scope, Base

SQL = """
SELECT
  JSON_EXTRACT_SCALAR(protopayload_auditlog.responseJson,
    '$.metadata.name') AS name,
  JSON_EXTRACT_SCALAR(protopayload_auditlog.responseJson,
    '$.metadata.uid') AS uid,
  receiveTimestamp,
  protopayload_auditlog.methodName,
  JSON_EXTRACT_SCALAR(protopayload_auditlog.responseJson,
    '$.metadata.creationTimestamp') creationTimestamp,
  JSON_EXTRACT_SCALAR(protopayload_auditlog.responseJson,
    '$.status.containerStatuses[0].state.terminated.finishedAt') finishedAt
FROM
  `primehub-demo.usage_pod_events.cloudaudit_googleapis_com_activity_202008*`
WHERE
  resource.labels.cluster_name="primary"
  AND (protopayload_auditlog.methodName ='io.k8s.core.v1.pods.create'
    OR protopayload_auditlog.methodName ='io.k8s.core.v1.pods.delete')
  AND JSON_EXTRACT_SCALAR(protopayload_auditlog.responseJson,
    "$.metadata.annotations['primehub.io/usage']") IS NOT NULL
"""

PROJECT_ID = 'primehub-demo'
db_connection = 'postgresql://postgres:mysecretpassword@localhost:5432/postgres'


class UsageValidation(Base):
    """
    usage validation only is used with external data validation (like BigQuery dataset)
    """
    __tablename__ = 'bigquery_usages'
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


def import_from_bigquery():
    client = bigquery.Client(PROJECT_ID)
    for row in client.query(SQL).result():
        pod_name, uid, receiveTimestamp, method_name, creation_timestamp, finished_at = row

        with session_scope(db_connection) as s:
            u = s.query(UsageValidation).filter_by(uid=uid).one_or_none()
            if u is None:
                u = UsageValidation()
                u.uid = uid
                u.pod_name = pod_name

                # we dont care other attributes
                u.group_name = ''
                u.user_name = ''
                u.component = ''
                u.component_name = ''
                u.instance_type = ''
                gpu, cpu, memory = 0, 0, 0
                u.gpu = gpu
                u.cpu = cpu
                u.memory = memory

            if method_name == 'io.k8s.core.v1.pods.create':
                u.scheduled_time = creation_timestamp
            else:
                u.scheduled_time = creation_timestamp
                if finished_at is None:
                    u.finished_time = receiveTimestamp
                else:
                    u.finished_time = finished_at

            s.add(u)
        print(row)


if __name__ == '__main__':
    # this modulde depends on google-cloud-bigquery
    # please execute `pip install` before using it
    import_from_bigquery()
