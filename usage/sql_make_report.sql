SELECT
  t.component,
  t.group_name,
  t.user_name,
  (t.cpu * t.time_used) AS cpu_gb_hours,
  (t.gpu * t.time_used) AS gpu_gb_hours,
  (t.memory * t.time_used) AS gb_memory_hours,
  t.time_used AS usage_hours,
  running
  FROM (
    SELECT
      component,
      group_name,
      user_name,
      MAX(cpu) AS cpu,
      MAX(gpu) AS gpu,
      (MAX(memory)/1024/1024/1024) AS memory,
      SUM(time_used_in_seconds)/3600
        AS time_used,
      MAX(running) AS running
    FROM
      %s
    GROUP BY
      group_name, user_name, instance_type, component
) t;