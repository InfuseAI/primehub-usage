from usage import generate_db_connection, logger
from usage.model import session_scope
from usage.report import generate_reports

if __name__ == '__main__':
    logger.info('generate report')
    with session_scope(generate_db_connection()) as s:
        generate_reports(s)
