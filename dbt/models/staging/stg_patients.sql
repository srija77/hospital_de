select patient_id,patient_name,email,phone,date_of_birth,city,updated_at
from {{ source('silver','patient_versions') }}
