"""Exact paired submission names; final mode requires actual evidence declarations."""
import argparse
import json
import shutil
import zipfile
from pathlib import Path
from html import escape
from hospital.live import ROOT

SOURCE_DIRS=['hospital','sql','dbt','migrations','.github','config','scripts','tests','docs','examples','evidence']
EXCLUDED={'target','logs','__pycache__','.venv','.tools'}


def code_zip(path,phase,root=ROOT):
    files={}
    for folder in SOURCE_DIRS:
        for source in (root/folder).rglob('*'):
            if source.is_file() and not any(p in EXCLUDED for p in source.parts):
                if source.suffix in ('.p8','.pem','.pyc') or source.name in ('profiles.yml','connections.toml'):
                    continue
                if folder=='evidence' and source.name not in ('manifest.example.json','incident_template.md'):
                    continue
                if source.suffix not in ('.py','.sql','.md','.csv','.json','.yml','.ps1','.svg','.png'):
                    continue
                files[source.relative_to(root).as_posix()]=source
    for name in ['README.md','requirements.txt','requirements-lock.txt','.gitignore','IMPLEMENTATION_PLAN.md']:
        if (root/name).exists():
            files[name]=root/name
    aliases={
        7:{'producer/stream_producer.py':'scripts/stream_producer.py','bronze_ingest/bronze_ingest.sql':'sql/ingestion/setup.sql',
           'silver_merge.sql':'sql/ingestion/silver.sql','reconcile.sql':'sql/ingestion/reconciliation.sql'},
        8:{'schema.yml':'dbt/models/schema.yml','reconcile_phase5.sql':'sql/ingestion/reconcile_phase5.sql',
           'profiles.example.yml':'dbt/profiles.example.yml'},
        9:{'monitoring_queries.sql':'sql/monitoring/monitoring_queries.sql','alerts/alert_definitions.sql':'sql/monitoring/alert_definitions.sql',
           'alerts/detect_alerts.sql':'sql/monitoring/detect_alerts.sql','alerts/alert_procedure.sql':'sql/monitoring/alert_procedure.sql',
           'benchmark_queries.sql':'sql/optimization/benchmark_queries.sql','optimization_scripts.sql':'sql/optimization/optimization_scripts.sql'},
        10:{'grants.sql':'sql/security/grants.sql','masking_policies.sql':'sql/security/masking_policies.sql',
            'pii_tags.sql':'sql/security/pii_tags.sql','config.example.json':'config/config.example.json'}}
    for alias,source in aliases[phase].items():
        files[alias]=root/source
    if phase==8:
        for source in (root/'dbt').rglob('*'):
            if source.is_file() and not any(p in EXCLUDED for p in source.parts) and source.name!='profiles.yml':
                files['dbt_project/'+source.relative_to(root/'dbt').as_posix()]=source
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for name,source in sorted(files.items()):
            # Final scan protects against keys even if a text file was misnamed.
            data=source.read_bytes()
            if any((b'-----BEGIN '+kind+b'PRIVATE KEY-----') in data for kind in (b'',b'RSA ',b'EC ',b'ENCRYPTED ')):
                raise ValueError('Private key detected; packaging aborted')
            z.writestr(name,data)


def draft_pdf(path,phase,sections):
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak
    from reportlab.lib.styles import getSampleStyleSheet
    styles=getSampleStyleSheet()
    story=[]
    for section in sections:
        story += [Paragraph(f'Phase {phase}: {escape(section)}',styles['Title']),Spacer(1,24),
                  Paragraph('DRAFT: NO VERIFIED LIVE EVIDENCE',styles['Heading2']),
                  Paragraph('Complete the matching Markdown report template, insert actual evidence and sign contributions before final submission.',styles['BodyText']),
                  Spacer(1,24),Paragraph('Evidence / explanation / UTC timestamp / query ID / commit: ____________________',styles['BodyText']),PageBreak()]
    SimpleDocTemplate(str(path)).build(story)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--phase',type=int,choices=[7,8,9,10],required=True)
    p.add_argument('--draft',action='store_true')
    p.add_argument('--report')
    p.add_argument('--evidence-manifest')
    p.add_argument('--out',default='artifacts/submissions')
    a=p.parse_args()
    spec=json.loads((ROOT/'config/submissions.json').read_text())['phases'][str(a.phase)]
    out=Path(a.out)/('draft' if a.draft else 'final')/f'phase{a.phase}'
    out.mkdir(parents=True,exist_ok=True)
    pdf=out/spec['report']
    if a.draft:
        draft_pdf(pdf,a.phase,spec['sections'])
    else:
        if not a.report or not a.evidence_manifest:
            p.error('Final packaging requires --report and --evidence-manifest; use --draft for templates')
        report=Path(a.report)
        if not report.read_bytes().startswith(b'%PDF-'):
            p.error('Report must be a real consolidated PDF')
        manifest=json.loads(Path(a.evidence_manifest).read_text())
        if manifest.get('phase')!=a.phase or manifest.get('contribution_signed') is not True:
            p.error('Manifest must identify phase and declare actual signed contributions')
        for item in spec['evidence_items']:
            evidence_path=manifest.get('items',{}).get(item)
            if not evidence_path or not Path(evidence_path).is_file():
                p.error('Missing actual evidence: '+item)
        shutil.copyfile(report,pdf)
    code_zip(out/spec['code'],a.phase)
    print(str(out.resolve()))


if __name__=='__main__':
    main()
