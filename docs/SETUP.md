# Setup and execution

Install Python 3.12 or 3.13, create .venv and install requirements.txt. Activate it so python and dbt refer to the same environment. Copy dbt/profiles.example.yml to dbt/profiles.yml (ignored). On Linux use python3 -m venv .venv, source .venv/bin/activate and cp.

No credentials are necessary for generation, unit tests, structural validation, report generation or dbt parse. dbt compile/build/test/docs generate require the live account. A parse produces manifest lineage but cannot validate Snowflake SQL, grants or actual data tests.

In a dedicated teaching Snowflake account, an authorized administrator executes sql/security/environment_setup.sql in Snowsight. It creates two databases and two suspended XSMALL warehouses, and four roles. SECURITYADMIN creates roles; SYSADMIN creates databases and transfers ownership. Assign DE_ENGINEER to a separate DEV human/service user, DE_DEPLOYER only to the PROD automation service user, DE_ANALYST only to an analyst test user and DE_ADMIN to the authorized administrator. Do not grant inherited admin/deployer roles to engineer or analyst. Review PUBLIC and pre-existing user grants first.

sql/security/user_setup.example.sql supplies explicit dedicated-user creation and role assignments. Register a different public key per user; private keys never enter source control. Use the existing authorized admin rather than creating the optional admin test identity if your account policy requires it.

Use RSA key-pair authentication with a private key file outside the repository. Register only the public key on the Snowflake user. In a local DEV shell:
```powershell
$env:SNOWFLAKE_ACCOUNT = 'organization-account'
$env:SNOWFLAKE_USER = 'YOUR_DEV_SERVICE_USER'
$env:SNOWFLAKE_PRIVATE_KEY_PATH = 'C:\secure\dev_key.p8'
python -m hospital.live migrate
python -m hospital.core generate --profile demo
python -m hospital.live load
python -m hospital.dbt_run build
```

Never print the key, use credentials in command arguments or commit connections.toml. CLI live operations default to DE_ENGINEER/HOSPITAL_DEV/HOSPITAL_DEV_WH. PROD uses a different key and service identity through GitHub environment secrets only.

Snowflake dynamic masking and tags require a supported account edition (typically Enterprise or higher). Verify entitlements before the live lab. If unavailable, complete local SQL inspection and mark masking unverified; a view-only substitute does not prove native policy behavior.

Run the monitoring views after Gold exists, then alert_procedure.sql and seed_demo_scenarios.sql. Query all four views from Snowsight. To refresh actual Gold freshness, use python -m hospital.live gold-refresh after a successful external dbt run; the dbt_run wrapper does this automatically.

One-time authorized PROD bootstrap occurs through the same main workflow: migrations create schemas and policies, load the common synthetic dataset and dbt builds/tests Gold. Before onboarding an analyst, administrator executes grants.sql after production_check confirms four policy attachments. No future SELECT grant exposes new objects accidentally. Adding a user: register public key, grant only DE_ANALYST, then run the denied-access matrix. This is security administration, not manual model deployment.

Normal promotion: protected PR -> local tests and optional live DEV tests -> approved merge -> DEV migrate/load/dbt build -> production environment reviewer approval -> PROD migrate/load/dbt build -> read-only verification. Setup repository protections before the first production run.

Live DEV integration checks after load/build: set $env:RUN_SNOWFLAKE_TESTS='true', then python -m unittest discover -s tests/integration -v. These five tests require the frozen demo fixture, not mixed stream/benchmark sessions. Set the flag back to false for local-only verification. The three-identity PROD masking/deny suite is separate: python -m hospital.security_check.

Safe teardown: suspend both alert objects if created; stop the producer; export actual evidence; remove users' role grants and revoke integration usage; review exact HOSPITAL_DEV/HOSPITAL_PROD names in Snowsight. Only an authorized administrator may drop these two teaching databases and the two HOSPITAL_*_WH warehouses. Destructive SQL is intentionally not part of routine scripts. Dropping these objects removes their evidence. Delete local generated data only after retaining required manifests.
