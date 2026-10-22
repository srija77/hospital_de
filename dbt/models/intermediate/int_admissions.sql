select a.admission_id,p.patient_key,a.patient_id,a.admit_date,a.discharge_date,
 a.department,a.admission_type,a.bill_amount,a.status,a.updated_at,a.event_version,
 datediff('day',a.admit_date,a.discharge_date)::number(38,0) length_of_stay
from {{ ref('stg_admissions') }} a
left join {{ ref('int_patient_history') }} p on a.patient_id=p.patient_id
 and a.admit_date >= p.valid_from::date and (a.admit_date < p.valid_to::date or p.valid_to is null)
