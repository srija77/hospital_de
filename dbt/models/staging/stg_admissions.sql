select admission_id,patient_id,admit_date,discharge_date,department,admission_type,
 bill_amount,status,updated_at,event_version from {{ source('silver','admissions') }}
