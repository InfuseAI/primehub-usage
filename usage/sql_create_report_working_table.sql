 CREATE TABLE %s AS
 SELECT *,
    CASE
      WHEN scheduled_time < :start_date THEN :start_date
      ELSE scheduled_time
    END AS usage_start,
    CASE
      WHEN finished_time IS NULL AND :generated_date > :end_date THEN :end_date
      WHEN finished_time IS NULL THEN :generated_date
      WHEN finished_time > :end_date THEN :end_date
      ELSE
      finished_time
    END AS usage_end,
    EXTRACT(EPOCH FROM (
    CASE
      WHEN finished_time IS NULL AND :generated_date > :end_date THEN :end_date
      WHEN finished_time IS NULL THEN :generated_date
      WHEN finished_time > :end_date THEN :end_date
      ELSE
      finished_time
    END
    -
    CASE
      WHEN scheduled_time < :start_date THEN :start_date
      ELSE scheduled_time
    END
    )) AS time_used_in_seconds,
    CASE
      WHEN finished_time IS NULL AND :generated_date > :end_date THEN 'N'
      WHEN finished_time IS NULL THEN 'Y'
      ELSE 'N'
    END AS running
    FROM primehub_usages WHERE finished_time IS NULL AND
    (scheduled_time, NOW()) OVERLAPS (:start_date, :end_date)
UNION
SELECT *,
    CASE
      WHEN scheduled_time < :start_date THEN :start_date
      ELSE scheduled_time
    END AS usage_start,
    CASE
      WHEN finished_time IS NULL THEN :generated_date
      WHEN finished_time > :end_date THEN :end_date
      ELSE
      finished_time
    END AS usage_end,
    EXTRACT(EPOCH FROM (
    CASE
      WHEN finished_time IS NULL THEN :generated_date
      WHEN finished_time > :end_date THEN :end_date
      ELSE
      finished_time
    END
    -
    CASE
      WHEN scheduled_time < :start_date THEN :start_date
      ELSE scheduled_time
    END
    )) AS time_used_in_seconds,
    CASE
      WHEN finished_time IS NULL THEN 'Y'
      ELSE 'N'
    END AS running
    FROM primehub_usages WHERE finished_time IS NOT NULL AND
    (scheduled_time, finished_time) OVERLAPS (:start_date, :end_date)