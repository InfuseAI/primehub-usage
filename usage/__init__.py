import datetime
import logging
import os
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from dateutil.tz import tzutc
from kubernetes import config

logger = logging.getLogger('usage-collector')
logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s")
logger.setLevel(logging.INFO)


def load_text(filename):
    with open(os.path.join(os.path.dirname(__file__), filename), 'r') as f:
        return f.read()


def this_month_date_range():
    return month_date_range(datetime.datetime.now())


def month_date_range(reference_datetime):
    the_date = reference_datetime
    if isinstance(reference_datetime, datetime.datetime):
        the_date = reference_datetime.date()

    start_date = the_date.replace(day=1)
    end_date = start_date + relativedelta(months=1)
    return start_date, end_date


def last_month_date_range(reference_datetime):
    start_date, end_date = month_date_range(reference_datetime)
    return start_date - relativedelta(months=1), end_date - relativedelta(months=1)


def as_report_month(date):
    """
    convert a date to report date which only has %Y%m
    :param date:
    :return:
    """
    return date.strftime('%Y%m')


def generate_db_connection():
    host = os.environ.get('PRIMEHUB_USAGE_DB_HOST', '')
    user = os.environ.get('PRIMEHUB_USAGE_DB_USER', '')
    password = os.environ.get('PRIMEHUB_USAGE_DB_PASSWORD', '')

    logger.info('database info, host={}, user={}'.format(host, user))
    db_connection = 'postgresql://{}:{}@{}:5432/postgres'.format(user, password, host)
    return db_connection


def load_kubernetes_config():
    try:
        config.load_kube_config()
        logger.info("load local kube-config")
        return
    except Exception as e:
        logger.warning("Failed to load kube-config, try in-cluster mode")

    config.load_incluster_config()
    logger.info("load in-cluster kube-config")


def format_value(value):
    if isinstance(value, str):
        return value
    if isinstance(value, Decimal):
        return "%.5f" % value
    if isinstance(value, float):
        return "%.5f" % value
    if isinstance(value, datetime.datetime):
        return str(value.replace(microsecond=0))
    return str(value)


def utc_now():
    return datetime.datetime.now(tz=tzutc()).replace(microsecond=0)
