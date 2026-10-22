select * from {{ ref('fct_admissions') }} where length_of_stay < 0 or discharge_date < admit_date
