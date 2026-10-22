CREATE TAG IF NOT EXISTS GOVERNANCE.PII_CLASSIFICATION ALLOWED_VALUES 'SENSITIVE','INTERNAL';
-- The dbt post-hook binds this tag to every PII Gold column after each build.
