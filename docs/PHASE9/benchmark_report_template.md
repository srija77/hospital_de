# Before/after benchmark report template

Student/team/date: [fill]. Dataset manifest hash and rows: [fill]. Snowflake query-history scope and privileges: [fill]. Warehouse, size, warm-up, cache state and repeats: [fill]. Baseline captured before modifications: [query IDs + artifact timestamp]. Rank the three baseline medians and identify the slowest.

| Workload | Before runtime | After runtime | Runtime change % | Before cost | After cost | Cost change % |
|---|---:|---:|---:|---:|---:|---:|
| department summary | [measured] | [measured] | [computed] | [attributed or N/A] | [attributed or N/A] | [computed or N/A] |
| monthly billing | [measured] | [measured] | [computed] | [attributed or N/A] | [attributed or N/A] | [computed or N/A] |
| patient join | [measured] | [measured] | [computed] | [attributed or N/A] | [attributed or N/A] | [computed or N/A] |

Generate from actual records: python -m hospital.core report --input artifacts/measurements.json --out artifacts/report. Embed runtime.svg and the generated table. change %=(after-before)/before*100. Negative values are improvement; zero/missing denominators produce N/A. Medians avoid selecting the fastest isolated run. Credits are attributed compute when available, exclude idle and are not total invoice cost; attach warehouse metering as separate context.

For each experiment state the variable changed, logical result hash equality, median runtime/scan evidence, cost availability, result, limitations and rollback. Explain if Snowflake optimized away the query rewrite or if layout/warehouse size did not help. Do not invent a gain.

Acceptance: baseline-slowest workload runtime improvement >=30%. Status [PASS / NOT MET / UNVERIFIED]. If NOT MET, inspect Query Profile, test an appropriate new one-variable optimization and retain the previous unsuccessful measurements. No benchmark acceptance claim without live measurements and comparable conditions.

Synthetic interface mode: python -m hospital.core report --input examples/benchmarks_synthetic.json --out artifacts/example-report. This output is unverified and cannot be submitted as benchmark proof.
