-- workload:department:before
SELECT department,admit_date,COUNT(*) admissions,SUM(bill_amount) billing
FROM GOLD.FCT_ADMISSIONS WHERE TO_VARCHAR(admit_date,'YYYY-MM-DD') LIKE '2025-%' GROUP BY department,admit_date;
-- workload:department:after
SELECT department,admit_date,COUNT(*) admissions,SUM(bill_amount) billing
FROM GOLD.FCT_ADMISSIONS WHERE admit_date>='2025-01-01' AND admit_date<'2026-01-01' GROUP BY department,admit_date;
-- workload:billing:before
SELECT DATE_TRUNC('month',admit_date) billing_month,SUM(bill_amount) billing
FROM GOLD.FCT_ADMISSIONS WHERE TO_VARCHAR(admit_date,'YYYY-MM-DD') LIKE '2025-%' GROUP BY billing_month;
-- workload:billing:after
SELECT DATE_TRUNC('month',admit_date) billing_month,SUM(bill_amount) billing
FROM GOLD.FCT_ADMISSIONS WHERE admit_date>='2025-01-01' AND admit_date<'2026-01-01' GROUP BY billing_month;
-- workload:patient_join:before
SELECT p.city,a.department,COUNT(*) admissions,SUM(a.bill_amount) billing
FROM (SELECT * FROM GOLD.FCT_ADMISSIONS) a JOIN GOLD.DIM_PATIENTS p ON a.patient_key=p.patient_key
WHERE TO_VARCHAR(a.admit_date,'YYYY-MM-DD') LIKE '2025-%' AND p.city='Chennai' GROUP BY p.city,a.department;
-- workload:patient_join:after
WITH a AS (SELECT patient_key,department,bill_amount FROM GOLD.FCT_ADMISSIONS
 WHERE admit_date>='2025-01-01' AND admit_date<'2026-01-01'),
p AS (SELECT patient_key,city FROM GOLD.DIM_PATIENTS WHERE city='Chennai')
SELECT p.city,a.department,COUNT(*) admissions,SUM(a.bill_amount) billing
FROM a JOIN p ON a.patient_key=p.patient_key GROUP BY p.city,a.department;
