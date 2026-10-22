# Reports and exact ZIP filenames

Run python -m hospital.package --phase 9 --draft (repeat 7,8,10) to generate a draft PDF report and runnable code ZIP under artifacts/submissions/draft/phase9/. Every draft PDF is marked DRAFT: NO VERIFIED LIVE EVIDENCE. These are teaching templates, not completed student submissions.

Author the final consolidated PDF from docs/templates/phaseN_report.md, in exact PDF page order, insert actual screenshots/results, sign the contribution statement and include chart conclusions. No fabricated evidence or generated signature. Each phase submits exactly two files with names specified in config/submissions.json.

For final packaging create evidence/phase9.json from evidence/manifest.example.json, populate every evidence_items key from config/submissions.json with an actual existing evidence path, and set contribution_signed only after signing. Run:
python -m hospital.package --phase 9 --report evidence/phase9_report.pdf --evidence-manifest evidence/phase9.json

The script validates PDF header, evidence-file existence and signed declaration, then produces phase9_report.pdf plus phase9_code.zip in the final phase folder. It cannot certify the truth of a signature, screenshot, mentor approval or measurement; those remain instructor review gates. The final PDF must contain the evidence, not merely reference loose files.

ZIP allowlist excludes keys, credentials, private profiles, virtual environments, generated data, artifacts and supplied reference documents. Alias paths preserve PDF-requested layout: producer/stream_producer.py, bronze_ingest/, silver_merge.sql, dbt_project/, schema.yml, reconcile_phase5.sql, monitoring_queries.sql, alerts/, benchmark_queries.sql, optimization_scripts.sql, grants.sql and masking_policies.sql. The actual runnable source layout is also included. Do not add live credentials to a ZIP.
