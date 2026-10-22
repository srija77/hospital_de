"""Generate fake hospital patients with sensitive-looking (but synthetic) PII."""
import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIRST = ['Aarav', 'Diya', 'Karthik', 'Meera', 'Rahul', 'Priya', 'Arjun', 'Lakshmi', 'Vikram', 'Ananya',
         'Suresh', 'Kavya', 'Nikhil', 'Divya', 'Ravi', 'Sneha', 'Ganesh', 'Pooja', 'Manoj', 'Asha']
LAST = ['Iyer', 'Reddy', 'Sharma', 'Nair', 'Kumar', 'Menon', 'Rao', 'Pillai', 'Gupta', 'Das']
BRANCHES = ['Chennai', 'Bengaluru', 'Hyderabad']
DIAGNOSES = ['Hypertension', 'Type 2 Diabetes', 'Asthma', 'Fracture', 'Migraine', 'Pneumonia', 'Appendicitis']
COLUMNS = ['PATIENT_ID', 'FULL_NAME', 'EMAIL', 'PHONE', 'DATE_OF_BIRTH', 'AADHAAR_NUMBER', 'INSURANCE_ID',
           'BRANCH', 'DIAGNOSIS', 'BILL_AMOUNT', 'ADMITTED_ON']


def generate(rows=200, seed=7):
    rng = random.Random(seed)
    out = []
    for i in range(1, rows + 1):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        out.append({
            'PATIENT_ID': i,
            'FULL_NAME': f'{first} {last}',
            'EMAIL': f'{first.lower()}.{last.lower()}{i}@example.com',
            'PHONE': f'9{rng.randint(100000000, 999999999)}',
            'DATE_OF_BIRTH': (date(1950, 1, 1) + timedelta(days=rng.randrange(365 * 55))).isoformat(),
            'AADHAAR_NUMBER': ' '.join(str(rng.randint(1000, 9999)) for _ in range(3)),
            'INSURANCE_ID': f'INS-{rng.randint(100000, 999999)}',
            'BRANCH': rng.choice(BRANCHES),
            'DIAGNOSIS': rng.choice(DIAGNOSES),
            'BILL_AMOUNT': round(rng.uniform(2000, 250000), 2),
            'ADMITTED_ON': (date(2026, 1, 1) + timedelta(days=rng.randrange(290))).isoformat(),
        })
    return out


def write(path=HERE / 'data' / 'patients.csv', rows=200, seed=7):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(generate(rows, seed))
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rows', type=int, default=200)
    parser.add_argument('--seed', type=int, default=7)
    args = parser.parse_args()
    print('Wrote', write(rows=args.rows, seed=args.seed))
