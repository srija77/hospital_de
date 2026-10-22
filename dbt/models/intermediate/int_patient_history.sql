select md5(patient_id::varchar||'|'||to_varchar(updated_at,'YYYY-MM-DD"T"HH24:MI:SS.FF9TZH:TZM'))::varchar patient_key,
 patient_id,patient_name,email,phone,date_of_birth,city,updated_at valid_from,
 lead(updated_at) over (partition by patient_id order by updated_at)::timestamp_tz valid_to,
 (lead(updated_at) over (partition by patient_id order by updated_at) is null)::boolean is_current
from {{ ref('stg_patients') }}
