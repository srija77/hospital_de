"""Create a concrete reviewable change without editing an applied migration."""
from hospital.live import ROOT


def main():
    path=ROOT/'migrations/V003__release_v_two.sql'
    if path.exists():
        raise SystemExit('V003 already exists; use a new migration number')
    path.write_text("CREATE OR REPLACE VIEW GOLD.RELEASE_INFO AS SELECT 'v2'::VARCHAR RELEASE_VERSION;\n")
    print('Created migrations/V003__release_v_two.sql; review, commit and open a PR')


if __name__=='__main__':
    main()
