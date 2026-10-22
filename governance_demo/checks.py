"""Offline checks run on every pull request (no Snowflake needed).

Governance rules enforced in CI:
  1. Migrations are named V001__name.sql, numbered without gaps, and end with ';'.
  2. Every personal-data column in the CLINICAL schema carries a PII_TYPE tag (so it is masked).
  3. Nothing is granted to PUBLIC, and only GOV_ADMIN may use the GOVERNANCE schema.
  4. Generated demo data uses only reserved example.com addresses.
"""
import re
import sys
from pathlib import Path

from generate_data import generate

HERE = Path(__file__).resolve().parent
PII_NAME = re.compile(r'NAME|EMAIL|PHONE|MOBILE|BIRTH|DOB|AADHAAR|PAN_|PASSPORT|ADDRESS|INSURANCE|CONTACT', re.I)


def strip_comments(sql):
    return re.sub(r'--[^\n]*', '', sql)


def clinical_columns(sql):
    """Columns created in CLINICAL tables, via CREATE TABLE or ALTER TABLE ... ADD COLUMN."""
    cols = set()
    for body in re.findall(r'CREATE\s+(?:OR\s+REPLACE\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?CLINICAL\.\w+\s*\((.*?)\)\s*(?:COMMENT|;)',
                           sql, re.I | re.S):
        cols.update(m.upper() for m in re.findall(r'^\s*(\w+)\s+[A-Z]', body, re.I | re.M))
    cols.update(m.upper() for m in re.findall(r'ALTER\s+TABLE\s+CLINICAL\.\w+\s+ADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)',
                                               sql, re.I))
    return cols


def run():
    errors = []
    files = sorted((HERE / 'migrations').glob('*.sql'))
    all_sql = ''
    for i, path in enumerate(files, start=1):
        if not re.fullmatch(r'V\d{3}__[a-z0-9_]+\.sql', path.name):
            errors.append(f'{path.name}: name must look like V006__add_something.sql')
        elif int(path.name[1:4]) != i:
            errors.append(f'{path.name}: expected version V{i:03} (no gaps or duplicates)')
        sql = strip_comments(path.read_text(encoding='utf-8'))
        if not sql.strip().endswith(';'):
            errors.append(f'{path.name}: last statement must end with ;')
        all_sql += sql + '\n'

    tagged = {m.upper() for m in re.findall(r'MODIFY\s+COLUMN\s+(\w+)\s+SET\s+TAG\s+GOVERNANCE\.PII_TYPE', all_sql, re.I)}
    for col in sorted(clinical_columns(all_sql)):
        if PII_NAME.search(col) and col not in tagged:
            errors.append(f'Column {col} looks like personal data but has no GOVERNANCE.PII_TYPE tag, so it would not be masked')

    if re.search(r'TO\s+ROLE\s+PUBLIC\b', all_sql, re.I):
        errors.append('Grants to PUBLIC are not allowed')
    for role in re.findall(r'ON\s+(?:SCHEMA|TABLE)\s+GOVERNANCE\b[.\w]*\s+TO\s+ROLE\s+(\w+)', all_sql, re.I):
        if role.upper() != 'GOV_ADMIN':
            errors.append(f'Only GOV_ADMIN may access the GOVERNANCE schema (found grant to {role})')

    if any(not r['EMAIL'].endswith('@example.com') for r in generate()):
        errors.append('Demo data must use example.com email addresses only')

    for e in errors:
        print('FAIL', e)
    print(f'{len(files)} migrations checked, {len(errors)} problem(s)')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(run())
