# Security design

Environment separation: HOSPITAL_DEV and HOSPITAL_PROD have separate object namespaces, warehouses and owners. DE_ENGINEER owns DEV, DE_DEPLOYER owns PROD. Separate users/keys are used for local DEV, analyst verification, administration and the protected production workflow. Config targets cannot silently point DEV SQL at PROD.

Least privilege: only DE_ANALYST receives explicit SELECT on two approved PROD Gold objects, plus database/schema/warehouse USAGE. It receives no future grants and no Bronze, Silver, staging or intermediate access. DE_ENGINEER has no production privileges. DE_ADMIN inherits each functional role for controlled setup. The production service owner is privileged by design and its secret must never be distributed to engineers.

PII classification: patient_name, email, phone and date_of_birth carry GOVERNANCE.PII_CLASSIFICATION=SENSITIVE in Gold through a dbt post-hook. The raw synthetic source is also documented as sensitive and is not analyst accessible. Tags label classification; explicit column masking policies enforce access. Tags alone do not mask.

Masking: CURRENT_ROLE()='DE_ADMIN' is the only authorized unmask condition. Others see MASKED, ***@***, ********** and NULL DOB. Analyst can read only the masked Gold dimension; no approved view projects raw PII. Real values in this capstone are synthetic. Native policies require the appropriate Snowflake edition; unavailable features are an unverified gate.

Persistence: dim_patients uses incremental MERGE, with full_refresh=false, so normal deploys preserve attached policies and grants rather than replacing an existing visible table. First creation has no analyst grants until policies and read-only deployment verification pass. Policy attachments are applied with FORCE after each build. All four PII tags are also reapplied. Grant changes occur separately as audited security administration.

CI/CD: local tests run without secrets on every PR. Live DEV build/tests are optional, explicitly configured and limited to trusted PRs through a protected dev-ci environment. Protected main, required checks and reviewers prevent arbitrary branch deployment. DEV integration must succeed before the production environment reviewer releases the job. Production service key is environment-scoped; no key is echoed. Migration checksums and dbt artifacts tie deployment to a commit.

Evidence: run hospital.security_check with separate users, retain assertions.json, query IDs and actual two-role screenshots. Audit role inheritance, ownership, PUBLIC and secondary roles first. Query-level denials complement screenshots. No row-level policy is used because this dataset has no authorized row segmentation requirement; do not claim one was tested.
