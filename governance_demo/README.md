# Snowflake demo: governance, privacy, CI/CD and monitoring

A small, self-contained demo built on the hospital theme. It uses one table, `CLINICAL.PATIENTS`, with 200 fake patients, and covers four topics:

| Topic | What the demo shows | Where |
|---|---|---|
| **Data governance** | Tags for owner, domain, sensitivity and PII type. Column comments. Least-privilege roles and grants. | `V002`, `V005` |
| **Privacy (sensitive data)** | Tag-based masking: tag a column and it is masked automatically. Partial masking. Row-level security by branch. | `V003`, `V004` |
| **CI/CD** | Versioned migrations. Pull-request checks that block untagged PII. Automatic DEV deployment. PROD deployment after approval. A data-quality gate. | `checks.py`, `deploy.py`, `.github/workflows/governance-demo.yml` |
| **Monitoring** | Data-quality checks. A log of who read the patient table. Deployment history. An alert that logs failures. | `V006` |

This folder doesn't depend on the rest of the hospital project.

## Who sees what

| | GOV_ADMIN | GOV_DOCTOR | GOV_ANALYST | GOV_DEPLOYER (pipeline) |
|---|---|---|---|---|
| Rows | 200, all branches | **69, Chennai only** | 200 | 200 |
| FULL_NAME | Suresh Sharma | visible | `***MASKED***` | `***MASKED***` |
| EMAIL | suresh.sharma1@example.com | visible | `*****@example.com` | `*****@example.com` |
| PHONE | 9523938499 | visible | `******8499` | `******8499` |
| DATE_OF_BIRTH | 1954-05-02 | visible | `1954-01-01` | `1954-01-01` |
| AADHAAR_NUMBER | 2186 9779 2542 | `XXXX XXXX 4800` | `XXXX XXXX 2542` | `XXXX XXXX 2542` |
| INSURANCE_ID | INS-483452 | visible | `***MASKED***` | `***MASKED***` |

These results were verified on the live account.

## Files

```
governance_demo/
  setup/00_admin_bootstrap.sql   one-time ACCOUNTADMIN setup: roles, warehouse, DEV/PROD databases
  migrations/V001..V006          everything else, deployed only by the pipeline
  generate_data.py               writes data/patients.csv (fake, deterministic)
  deploy.py                      applies pending migrations, loads data, runs the quality gate
  checks.py                      offline pull-request checks (governance guardrails)
  demo_queries.sql               the live demo script, in four parts
```

## Pipeline

```
pull request ──► checks.py (no Snowflake)
                 · migration naming and order
                 · every PII column carries a PII_TYPE tag
                 · no grants to PUBLIC, GOVERNANCE schema for GOV_ADMIN only
merge to main ─► deploy DEV  (migrate → load → quality gate)
              └► deploy PROD (waits for reviewer approval, same steps)
```

`deploy.py` records every migration in `CONTROL.MIGRATION_HISTORY`. It refuses to run an applied migration that has since been edited, stops if any data-quality rule fails, and refuses `--env prod` outside GitHub Actions.

## Setup

Your Snowflake account is already set up: roles, warehouse `GOV_DEMO_WH`, databases `GOV_DEMO_DEV` and `GOV_DEMO_PROD`, and the service user `GOV_CI_USER` with key-pair auth. DEV is deployed through V006.

For GitHub, under *Settings → Environments*, create:
- `dev`
- `production`, with **Required reviewers** turned on

Add these three secrets to **both** environments:

| Secret | Value |
|---|---|
| `SNOWFLAKE_ACCOUNT` | your account identifier (`ORG-ACCOUNT`) |
| `SNOWFLAKE_USER` | `GOV_CI_USER` |
| `SNOWFLAKE_PRIVATE_KEY` | full contents of `%USERPROFILE%\.snowflake\gov_ci_key.p8`, including the BEGIN/END lines |

Then re-run the *Governance demo* workflow from the Actions tab.

To deploy DEV locally:

```powershell
$env:SNOWFLAKE_ACCOUNT="<ORG-ACCOUNT>"; $env:SNOWFLAKE_USER="GOV_CI_USER"
$env:SNOWFLAKE_PRIVATE_KEY_PATH="$HOME\.snowflake\gov_ci_key.p8"
python governance_demo/checks.py
python governance_demo/deploy.py --env dev --load-data
```

## Demo flow (about 25 minutes)

1. **Privacy (5 min).** Run part 1 of `demo_queries.sql`. The same `SELECT` returns different results for each role, and the analyst can still do useful analysis.
2. **Governance (5 min).** Run part 2. It shows the tags on every column, the policies protecting the table, the branch mapping, and automatic classification with `SYSTEM$CLASSIFY`.
3. **CI/CD (10 min).**
   1. On a branch, add `migrations/V007__add_emergency_contact.sql`:
      ```sql
      ALTER TABLE CLINICAL.PATIENTS ADD COLUMN EMERGENCY_CONTACT_PHONE VARCHAR;
      ```
   2. Open a pull request. **checks** fails: *"EMERGENCY_CONTACT_PHONE looks like personal data but has no GOVERNANCE.PII_TYPE tag"*.
   3. Add the tag line and push again. The checks pass.
      ```sql
      ALTER TABLE CLINICAL.PATIENTS MODIFY COLUMN EMERGENCY_CONTACT_PHONE SET TAG GOVERNANCE.PII_TYPE = 'PHONE';
      ```
   4. Merge. DEV deploys on its own and PROD waits for approval.
   5. Query the new column as GOV_ANALYST. It's already masked, because the masking policy is attached to the tag.
   6. Run part 3 of `demo_queries.sql` to show V007 in both environments.
4. **Monitoring (5 min).** Run part 4. All checks pass. Insert a bad row and three rules fail. `EXECUTE ALERT` writes the failures to `ALERT_LOG`. Then clean up. The same checks run as the pipeline's quality gate, so bad data never reaches PROD.

## Reset

```sql
USE ROLE ACCOUNTADMIN;
DROP DATABASE IF EXISTS GOV_DEMO_DEV;
DROP DATABASE IF EXISTS GOV_DEMO_PROD;
-- then rerun setup/00_admin_bootstrap.sql and deploy again
```

## Notes

- Masking policies use `IS_ROLE_IN_SESSION`, so role inheritance counts. SYSADMIN and ACCOUNTADMIN inherit GOV_ADMIN and see everything. That's why `demo_queries.sql` starts with `USE SECONDARY ROLES NONE`.
- The alert is created **suspended** so it costs nothing. `ALTER ALERT ... RESUME` runs it hourly.
- `PII_ACCESS_LOG` reads `SNOWFLAKE.ACCOUNT_USAGE`, which lags by up to about 3 hours.
- Masking and row access policies need Snowflake Enterprise edition or higher.
