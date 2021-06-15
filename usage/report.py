from sqlalchemy import text, distinct

from usage import load_text, this_month_date_range, last_month_date_range, as_report_month, format_value
from usage.model import session_scope, MonthlyReport


def _date_func(x):
    # convert report date '202007' to ('2020', '7')
    if len(x) < 6:
        raise ValueError('invalid report date: {}'.format(x))
    return "{}/{}".format(x[:4], str(int(x[4:6], 10)))


def find_monthly_report_keys(session):
    keys = session.query(distinct(MonthlyReport.report_month)).all()
    return [_date_func(x[0]) for x in sorted(keys, reverse=True)]


def get_monthly_report_by_key(session, key):
    q = session.query(MonthlyReport).filter(MonthlyReport.report_month == key)
    outputs = [MonthlyReport.get_csv_headers()]
    outputs += [x.to_csv_entry() for x in q.all()]
    return "\n".join(outputs)


def get_monthly_details_report_by_key(session, key):

    table = "report_%s" % key
    query = text(load_text('sql_query_details.sql') % table)

    # csv headers
    outputs = ["report_month,group,user,component,component_name,"
               "cpu_core_hours,gpu_core_hours,gb_memory_hours,usage_hours,"
                "instance_type,instance_cpu_core,instance_gpu_core,instance_memory_gb,"
                "pod_name,k8s_uid,start_time,end_time,running"]

    for row in session.bind.execute(query).fetchall():
        output_row = list(row)
        output_row.insert(0, key)
        output_row = [format_value(x) for x in output_row]
        outputs.append(",".join(output_row))
    return "\n".join(outputs)


def generate_reports(session):
    start_date, end_date = this_month_date_range()
    generate_report(session, start_date, end_date)

    start_date, end_date = last_month_date_range(start_date)
    generate_report(session, start_date, end_date)


def generate_report(session, start_date, end_date):
    create_report_working_table(session, start_date, end_date)


def create_report_working_table(session, start_date, end_date):
    from datetime import date, timedelta

    table = "report_%s" % as_report_month(start_date)
    ddl = text(load_text('sql_create_report_working_table.sql') % table) \
        .bindparams(start_date=start_date, end_date=end_date, generated_date=date.today() + timedelta(days=1))

    # create temp table
    session.bind.execute('DROP TABLE IF EXISTS %s' % table)
    session.bind.execute(ddl)

    # generate report
    the_date = as_report_month(start_date)
    session.query(MonthlyReport).filter(MonthlyReport.report_month == the_date).delete()
    for row in session.bind.execute(load_text('sql_make_report.sql') % table).fetchall():
        r = MonthlyReport()
        r.component, r.group_name, r.user_name, r.cpu_core_hours, r.gpu_core_hours, r.gb_memory_hours, r.usage_hours, r.running = row
        r.report_month = the_date
        session.add(r)


if __name__ == '__main__':
    db_connection = 'postgresql://postgres:mysecretpassword@localhost:5432/postgres'
    with session_scope(db_connection) as s:
        generate_reports(s)
        csv = get_monthly_details_report_by_key(s, '202010')
        print(csv)
        csv = get_monthly_report_by_key(s, '202010')
        print(csv)