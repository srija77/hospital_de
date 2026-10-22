{% snapshot patient_snapshot %}
{{ config(target_schema='INTERMEDIATE',alias=var('snapshot_alias','patient_snapshot'),unique_key='patient_id',strategy='timestamp',updated_at='updated_at') }}
select * from {{ ref('stg_patients') }}
where updated_at <= '{{ var("snapshot_as_of", "2099-01-01") }}'::timestamp_tz
qualify row_number() over (partition by patient_id order by updated_at desc)=1
{% endsnapshot %}
