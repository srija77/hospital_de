# Snowflake demo: data governance, CI/CD and sensitive data

A small, self-contained demo built on the hospital theme. It uses one table, `CLINICAL.PATIENTS`, with 200 fake patients, and covers three topics:

| Topic | What the demo shows | Where |
|---|---|---|
| **Data governance** | Tags for owner, domain, sensitivity and PII type. Column comments. Least-privilege grants. Tag, policy and access-history queries. | `V002`, `V005`, `demo_queries.sql` part 2 |
| **Sensitive data** | Tag-based masking: tag a column once and it is masked automatically. Partial masking. Row-level security by hospital branch. | `V003`, `V004`, `demo_queries.sql` part 1 |
| **CI/CD** | Versioned migrations. Pull-request checks that block untagged PII. Automatic DEV deployment. PROD deployment after approval. Deployment history in Snowflake. | `checks.py`, `deploy.py`, `.github/workflows/governance-demo.yml` |

This folder doesn't depend on the rest of the hospital project, which is unchanged.

## Who sees what

| Column | GOV_ADMIN | GOV_DOCTOR | GOV_ANALYST |
|---|---|---|---|
| Rows | all branches | **Chennai only** | all branches |
| FULL_NAME | Suresh Sharma | Suresh Sharma | `***MASKED***` |
| EMAIL | suresh.sharma1@example.com | same | `*****@example.com` |
| PHONE | 9523938499 | same | `******8499` |
| DATE_OF_BIRTH | 1954-05-02 | same | `1954-01-01` (year only) |
| AADHAAR_NUMBER | 2186 9779 2542 | `XXXX XXXX 2542` | `XXXX XXXX 2542` |
| INSURANCE_ID | INS-483452 | same | `***MASKED***` |
| DIAGNOSIS, BILL_AMOUNT | visible | visible | visible |

## Files

```
governance_demo/
  setup/00_admin_bootstrap.sql   one-time ACCOUNTADMIN setup: roles, warehouse, DEV/PROD databases, CI user
  migrations/V001..V005          everything else, deployed only by the pipeline
  generate_data.py               writes data/patients.csv (fake, deterministic)
  deploy.py                      applies pending migrations, loads data, records history
  checks.py                      offline pull-request checks (governance guardrails)
  demo_queries.sql               the live demo script
```

## One-time setup

1. **Snowflake.** As ACCOUNTADMIN, run `setup/00_admin_bootstrap.sql`. Create a key pair as described in its comments, uncomment the `GOV_CI_USER` block, and grant the three people roles to your own user.
2. **GitHub.** Create two environments under *Settings → Environments*: `dev`, and `production` with **Required reviewers** turned on. Add these secrets to both:
   - `SNOWFLAKE_ACCOUNT`, for example `abc12345.ap-south-1.aws`
   - `SNOWFLAKE_USER`, set to `GOV_CI_USER`
   - `SNOWFLAKE_PRIVATE_KEY`, the full contents of `gov_ci_key.p8`

To try it locally first (DEV only):

```powershell
.\.venv\Scripts\Activate.ps1
$env:SNOWFLAKE_ACCOUNT="..."; $env:SNOWFLAKE_USER="..."; $env:SNOWFLAKE_PASSWORD="..."  # or SNOWFLAKE_PRIVATE_KEY_PATH
python governance_demo/checks.py
python governance_demo/deploy.py --env dev --load-data
```

`deploy.py --env prod` refuses to run outside GitHub Actions, so PROD only changes through the pipeline.

## Demo flow (about 20 minutes)

**1. Sensitive data (5 min).** Run part 1 of `demo_queries.sql`. The same `SELECT` returns different results as GOV_ADMIN, GOV_DOCTOR and GOV_ANALYST. Point out that the analyst can still group by branch, diagnosis and birth year.

**2. Governance (5 min).** Run part 2. Show the tags on every column, which policies protect the table, the branch mapping table, and the access history (who read the patient table). `SYSTEM$CLASSIFY` shows Snowflake detecting the sensitive columns automatically.

**3. CI/CD (10 min).** Show the governance guardrail catching a mistake.

1. On a branch, add `governance_demo/migrations/V006__add_emergency_contact.sql`:
   ```sql
   ALTER TABLE CLINICAL.PATIENTS ADD COLUMN EMERGENCY_CONTACT_PHONE VARCHAR;
   ```
2. Open a pull request. The **checks** job fails: *"Column EMERGENCY_CONTACT_PHONE looks like personal data but has no GOVERNANCE.PII_TYPE tag"*.
3. Add the tag line and push again. The checks pass.
   ```sql
   ALTER TABLE CLINICAL.PATIENTS MODIFY COLUMN EMERGENCY_CONTACT_PHONE SET TAG GOVERNANCE.PII_TYPE = 'PHONE';
   ```
4. Merge. **deploy-dev** runs on its own. **deploy-prod** waits for a reviewer to approve.
5. Query the new column as GOV_ANALYST. It's already masked as `******1234`, with no policy change, because the masking policy is attached to the tag.
6. Run part 3 of `demo_queries.sql` to show V006 in the `CONTROL.MIGRATION_HISTORY` table of both databases.

You can also show that editing an applied migration (for example V002) makes the deployment fail with *"Never change an applied migration; add a new V file instead."*

## Reset

```sql
USE ROLE ACCOUNTADMIN;
DROP DATABASE IF EXISTS GOV_DEMO_DEV;
DROP DATABASE IF EXISTS GOV_DEMO_PROD;
-- then rerun setup/00_admin_bootstrap.sql
```

## Notes

- Masking policies use `IS_ROLE_IN_SESSION`, so role inheritance counts. SYSADMIN and ACCOUNTADMIN inherit GOV_ADMIN and see everything. That's why `demo_queries.sql` starts with `USE SECONDARY ROLES NONE`.
- Masking and row access policies need Snowflake **Enterprise edition** or higher.
- The existing `ci.yml` and `deploy.yml` workflows also run on pushes to `main`. Disable them in GitHub if you only want this demo's pipeline to run.
