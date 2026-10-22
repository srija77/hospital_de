{% macro apply_patient_security() %}
{% if target.name == 'prod' %}
alter table {{ this }} modify column patient_name set masking policy {{ target.database }}.GOVERNANCE.MASK_NAME force;
alter table {{ this }} modify column email set masking policy {{ target.database }}.GOVERNANCE.MASK_EMAIL force;
alter table {{ this }} modify column phone set masking policy {{ target.database }}.GOVERNANCE.MASK_PHONE force;
alter table {{ this }} modify column date_of_birth set masking policy {{ target.database }}.GOVERNANCE.MASK_DOB force;
alter table {{ this }} modify column patient_name set tag {{ target.database }}.GOVERNANCE.PII_CLASSIFICATION='SENSITIVE';
alter table {{ this }} modify column email set tag {{ target.database }}.GOVERNANCE.PII_CLASSIFICATION='SENSITIVE';
alter table {{ this }} modify column phone set tag {{ target.database }}.GOVERNANCE.PII_CLASSIFICATION='SENSITIVE';
alter table {{ this }} modify column date_of_birth set tag {{ target.database }}.GOVERNANCE.PII_CLASSIFICATION='SENSITIVE';
{% else %}
select 1;
{% endif %}
{% endmacro %}
