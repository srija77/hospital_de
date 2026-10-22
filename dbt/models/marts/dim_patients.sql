{{ config(materialized='incremental', unique_key='patient_key', incremental_strategy='merge', on_schema_change='fail', full_refresh=false, post_hook="{{ apply_patient_security() }}") }}
select patient_key,patient_id,patient_name,email,phone,date_of_birth,city,valid_from,valid_to,is_current
from {{ ref('int_patient_history') }}
