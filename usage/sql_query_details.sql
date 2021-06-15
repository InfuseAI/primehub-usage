SELECT
group_name,
user_name,
component,
component_name,
cpu * ((time_used_in_seconds)/3600) AS cpu_core_hours,
gpu * ((time_used_in_seconds)/3600) AS gpu_core_hours,
(memory/1024/1024/1024) * ((time_used_in_seconds)/3600) AS gb_memory_hours,
(time_used_in_seconds)/3600 AS usage_hours,
instance_type,
cpu AS instance_cpu_core,
gpu AS instance_gpu_core,
memory/1024/1024/1024 AS instance_memory_gb,
pod_name,
uid AS k8s_uid,
usage_start AS start_time,
usage_end AS end_time,
running
FROM %s
ORDER BY start_time, group_name, user_name