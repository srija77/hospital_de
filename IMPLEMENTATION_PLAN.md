# Implementation plan

1. Inspect references and repository. Initial inspection: workspace empty; PDFs and guides unavailable. Prompt is provisional acceptance specification; exact submission filenames remain pending.
2. Build deterministic shared hospital fixtures and local CDC/monitoring/report tests.
3. Build Snowflake Bronze/Silver ingestion and dbt history/Gold transformations.
4. Build Phase 9 dashboard, durable alert detection, benchmark collection and controlled experiments.
5. Build Phase 10 isolated databases, least privilege, masking and controlled migrations/CI.
6. Write reproducible instructor/student materials, evidence templates and packaging.
7. Run local checks and distinguish unexecuted Snowflake/GitHub checks.

No warehouse resizing, clustering, production deployment or paid account actions run automatically. Live operations require configured credentials and explicit experiment flags.

Completed: all eight reference documents read from the user-supplied ZIP; implementation and teaching materials written; 52 PDF deliverables mapped; 14 local verification stages passed (22 passing tests, five live tests skipped). See docs/VALIDATION.md for actual scope and outstanding live/human gates. Exact filenames are preserved by config/submissions.json and hospital.package.
