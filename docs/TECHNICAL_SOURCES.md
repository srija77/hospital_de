# Official implementation references

The supplied deliverable PDFs define acceptance. The following primary documentation was checked for implementation details:

- [Snowflake CREATE ALERT](https://docs.snowflake.com/en/sql-reference/sql/create-alert): scheduling, privileges and supported actions.
- [Snowflake alerts](https://docs.snowflake.com/en/user-guide/alerts): warehouse-backed versus serverless operation.
- [Column-level security](https://docs.snowflake.com/en/user-guide/security-column-intro): FORCE replaces a policy atomically and avoids an unmasked detach/reattach interval.
- [POLICY_REFERENCES](https://docs.snowflake.com/en/sql-reference/functions/policy_references): post-deploy masking attachment verification.
- [dbt Snowflake configurations](https://docs.getdbt.com/reference/resource-configs/snowflake-configs): incremental MERGE materialization.
- [dbt incremental models](https://docs.getdbt.com/docs/build/incremental-models): incremental strategy and Snowflake adapter compatibility.
- [schemachange](https://github.com/Snowflake-Labs/schemachange): reviewed migration alternative; this capstone instead supplies a compact checksum/history runner.

These references support SQL/design choices; they are not evidence that the user's account or GitHub configuration has been tested.
