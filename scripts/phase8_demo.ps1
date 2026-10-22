$ErrorActionPreference = 'Stop'
python -m hospital.contract_demo
if ($LASTEXITCODE -ne 0) { throw 'Contract correction did not pass' }
