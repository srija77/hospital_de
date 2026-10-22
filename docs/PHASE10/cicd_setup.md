# CI/CD setup and exact promotion scenario

GitHub configuration is an external prerequisite; YAML alone cannot enforce repository settings. Push this source into a repository, then configure:
1. Protect main: pull requests required, at least one reviewer, local job required, no force pushes, no direct pushes, and enforce for administrators where supported.
2. Create environments dev, dev-ci and production. Set production to main only; require an independent reviewer and prevent self-review where supported. Restrict service-key visibility to that environment.
3. Add SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER and SNOWFLAKE_PRIVATE_KEY secrets separately per environment. DEV identities hold only DE_ENGINEER; production identity holds only DE_DEPLOYER. Raw key content is written to a temporary restricted file and deleted in always() cleanup.
4. To run trusted PR integration, set repository variable ENABLE_SNOWFLAKE_TESTS=true and protect dev-ci with required reviewers. Require live-dev in branch rules once it is reliably available. Never approve untrusted PR code for secret access. Forks never receive live credentials.
5. Grant the separate service users their public keys in Snowflake, set default role/warehouse and restrict user grants. Do not use one unrestricted credential across environments.

PR workflow: Python unittest suite, structural SQL/config/workflow/secret-pattern checks, dbt parse, migration validation. dbt parse works with offline placeholders and cannot validate Snowflake queries. Optional credentialed live-dev migrates/loads/builds/tests the same hospital project in DEV. Migration checks run offline for naming/structure and live for actual compilation. CI must fail any required check failure.

Merge workflow: push to protected main re-runs local checks and dbt parse; DEV migrates, loads shared fixtures, builds/tests; production reviewer approves; PROD migrates, loads identical shared fixture, builds/tests, then production_check verifies release and four masking attachments. The code's PROD guard also rejects ordinary local command execution. Account RBAC/service-key protection is the actual security boundary; environment variables alone are not a security control.

Migration mechanism: V001 creates environment-relative schemas/tables/policies; V002 introduces release view. CONTROL.MIGRATION_HISTORY stores filename, SHA-256, timestamps and STARTED/SUCCESS. Applied-file changes fail. DDL auto-commits; interrupted STARTED migrations are rerun and must be idempotent. Global GitHub concurrency serializes promotions; DEV concurrency coordinates trusted PR integration and deployment. Do not run another migration process against the same database outside the workflow. Append new VNNN migration for corrections; never edit applied files.

Reproducible change demonstration (git/gh installed and authenticated, remote configured):
```powershell
git switch -c lab/approved-release-v2
python -m hospital.release_change
git add migrations/V003__release_v_two.sql
git commit -m "Promote hospital release marker to v2"
git push -u origin lab/approved-release-v2
gh pr create --title "Promote hospital release v2" --body "Updates the Gold release marker through the protected migration workflow."
```
hospital.release_change writes one exact additive migration. Show PR checks, obtain independent review, merge through GitHub, and capture main commit SHA. The production environment reviewer releases the authorized job. Do not approve your own review if prohibited.

Verify through a read-only administrator worksheet:
SELECT RELEASE_VERSION FROM HOSPITAL_PROD.GOLD.RELEASE_INFO;
Expect v2 after the approved deployment. Show CONTROL.MIGRATION_HISTORY with V003 SUCCESS, workflow run and commit. production_check checks existence and policies; the instructor explicitly checks v2 for this scenario.

Then query patient 1 as admin and separate analyst, show masks, attempt prohibited zero-row UPDATE and raw reads, and run engineer PROD denial. No direct model edit in PROD. If bootstrap deployment has not completed, do not fake the PR/deploy proof.

Rollback: revert model code in a new PR; for applied SQL append V004 corrective migration restoring release marker v1. Never delete history or edit V003. Run same DEV/build/approval/PROD path. First safe mitigation is pause downstream consumption/alerts as authorized, then fix forward. Runbook contains failure investigation and evidence steps.

External evidence: branch protection screenshot, production environment rules, PR review/checks, merge SHA, DEV and PROD job logs, migration history, actual v2 query, denied ordinary writes. Local static validation does not prove any repository settings or completed deployment.
