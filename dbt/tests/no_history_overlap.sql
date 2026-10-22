select patient_id from {{ ref('dim_patients') }} group by patient_id
having count_if(is_current) != 1
