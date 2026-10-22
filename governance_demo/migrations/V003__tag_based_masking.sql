-- SENSITIVE DATA: column masking driven by the PII_TYPE tag.
-- The policy is attached to the TAG, not to columns, so any column tagged PII_TYPE
-- (today or in a future migration) is masked with no extra work.

CREATE MASKING POLICY IF NOT EXISTS GOVERNANCE.PII_STRING_MASK AS (val VARCHAR) RETURNS VARCHAR ->
    CASE
        WHEN IS_ROLE_IN_SESSION('GOV_ADMIN') THEN val
        WHEN SYSTEM$GET_TAG_ON_CURRENT_COLUMN('GOVERNANCE.PII_TYPE') = 'NATIONAL_ID'
            THEN 'XXXX XXXX ' || RIGHT(val, 4)
        WHEN IS_ROLE_IN_SESSION('GOV_DOCTOR') THEN val
        WHEN SYSTEM$GET_TAG_ON_CURRENT_COLUMN('GOVERNANCE.PII_TYPE') = 'EMAIL'
            THEN '*****' || SUBSTR(val, POSITION('@' IN val))
        WHEN SYSTEM$GET_TAG_ON_CURRENT_COLUMN('GOVERNANCE.PII_TYPE') = 'PHONE'
            THEN '******' || RIGHT(val, 4)
        ELSE '***MASKED***'
    END
    COMMENT = 'Admin: full. Doctor: full except national ID. Others: partial or fully masked.';

CREATE MASKING POLICY IF NOT EXISTS GOVERNANCE.PII_DATE_MASK AS (val DATE) RETURNS DATE ->
    CASE
        WHEN IS_ROLE_IN_SESSION('GOV_ADMIN') OR IS_ROLE_IN_SESSION('GOV_DOCTOR') THEN val
        ELSE DATE_TRUNC('YEAR', val)
    END
    COMMENT = 'Others see only the birth year, enough for age-band analytics.';

ALTER TAG GOVERNANCE.PII_TYPE SET
    MASKING POLICY GOVERNANCE.PII_STRING_MASK,
    MASKING POLICY GOVERNANCE.PII_DATE_MASK;
