import os

from flask import Flask, jsonify

from usage import generate_db_connection, logger
from usage.model import session_scope
from usage.report import find_monthly_report_keys, get_monthly_report_by_key, get_monthly_details_report_by_key
import logging

app = Flask(__name__)
logger.setLevel(logging.WARNING)


@app.route('/report/monthly')
def list_monthly_reports():
    with session_scope(generate_db_connection()) as s:
        keys = find_monthly_report_keys(s)
        return jsonify(keys)


@app.route('/report/monthly/<int:year>/<int:month>')
def get_monthly_report(year, month):
    with session_scope(generate_db_connection()) as s:
        return get_monthly_report_by_key(s, "%04d%02d" % (year, month))


@app.route('/report/monthly/details/<int:year>/<int:month>')
def get_monthly_details_report(year, month):
    with session_scope(generate_db_connection()) as s:
        return get_monthly_details_report_by_key(s, "%04d%02d" % (year, month))


@app.route('/health')
def health_check():
    try:
        with session_scope(generate_db_connection()) as s:
            result = s.bind.execute('SELECT version()').fetchall()
            for row in result:
                return "HEALTH"
    except Exception as e:
        raise e


def configure_for_dev_locally():
    logger.warning('in local development mode (patch db to localhost)')
    os.environ.update({'PRIMEHUB_USAGE_DB_HOST': '127.0.0.1'})
    os.environ.update({'PRIMEHUB_USAGE_DB_USER': 'postgres'})
    os.environ.update({'PRIMEHUB_USAGE_DB_PASSWORD': 'mysecretpassword'})


if __name__ == "__main__":
    configure_for_dev_locally()
    app.run(host="0.0.0.0")
