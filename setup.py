#!/usr/bin/env python
import setuptools

setuptools.setup(
    name="primehub-usage",  # Replace with your own username
    version="0.0.1",
    author="qrtt1",
    author_email="qrtt1@infuseai.io",
    description="Resource Usage Monitoring and Reporting",
    packages=setuptools.find_packages(include=['usage', 'scripts/*']),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    scripts=['scripts/primehub-usage-watch.py',
             'scripts/primehub-usage-report-generator.py',
             'scripts/primehub-usage-running-pods-monitor.py',
             'scripts/primehub-usage-legacy-pods-helper.py'],
    data_files=[('usage', ['usage/sql_create_report_working_table.sql',
                           'usage/sql_make_report.sql',
                           'usage/sql_query_details.sql'])]
)
