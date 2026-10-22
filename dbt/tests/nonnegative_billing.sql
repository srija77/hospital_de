select * from {{ ref('fct_admissions') }} where bill_amount < 0
