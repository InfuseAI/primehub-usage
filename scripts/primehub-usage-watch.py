#!/usr/bin/env python
import os
import sys
import time

from usage import watcher, logger, generate_db_connection


def main():
    namespace = os.environ.get('PRIMEHUB_USAGE_WATCHED_NAMESPACE', None)
    if namespace is None:
        logger.error('env PRIMEHUB_USAGE_WATCHED_NAMESPACE is required')
        sys.exit(1)

    db_connection = generate_db_connection()

    while True:
        try:
            logger.info('start to watch namespace [{}]'.format(namespace))
            watcher.watch_events(namespace, db_connection)
        except Exception as e:
            logger.warning("Got exception, will retry it later")
            logger.exception(e)
            time.sleep(10)


if __name__ == '__main__':
    main()
