import datetime
import unittest

from dateutil.tz import tzutc

from usage import last_month_date_range, as_report_month
from usage import month_date_range


class TestUtils(unittest.TestCase):

    def test_range_picking_this_month(self):
        reference_datetime = datetime.datetime(2020, 7, 22, 4, 51, 22, tzinfo=tzutc())

        start_date, end_date = month_date_range(reference_datetime)
        self.assertEqual(datetime.date(2020, 7, 1), start_date)
        self.assertEqual(datetime.date(2020, 8, 1), end_date)

    def test_range_picking_last_month(self):
        reference_datetime = datetime.datetime(2020, 7, 22, 4, 51, 22, tzinfo=tzutc())

        start_date, end_date = last_month_date_range(reference_datetime)
        self.assertEqual(datetime.date(2020, 6, 1), start_date)
        self.assertEqual(datetime.date(2020, 7, 1), end_date)

    def test_to_report_month_string(self):
        self.assertEqual('202010', as_report_month(datetime.date(2020, 10, 24)))
        self.assertEqual('202001', as_report_month(datetime.date(2020, 1, 1)))


if __name__ == '__main__':
    unittest.main()
