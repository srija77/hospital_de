{{ config(materialized='incremental',unique_key='admission_id',incremental_strategy='merge',on_schema_change='fail') }}
-- Re-merge current Silver so late updates and dimension-key corrections are not lost to a date watermark.
select admission_id,patient_key,patient_id,admit_date,discharge_date,department,admission_type,
 {% if var('break_contract', false) %}bill_amount::varchar{% else %}bill_amount{% endif %} as bill_amount,
 status,updated_at,event_version,length_of_stay
from {{ ref('int_admissions') }}
{% if is_incremental() %}
where admission_id is not null
{% endif %}
