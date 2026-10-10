"""Reconstruct the blocked feasibility result from preserved primary-source evidence."""
import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil

PUBLIC_HEADERS = {'date','content-type','content-length','cache-control','server-timing','server','cf-ray'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def build(evidence, output):
    output.mkdir(parents=True, exist_ok=True)
    raw = evidence / 'sources'
    direct = json.loads((raw / 'ACQUISITION.json').read_text())
    if len(direct) != 1 or direct[0]['status'] != 403:
        raise ValueError('This bounded partial result is only for the recorded 403 failure')
    body = raw / direct[0]['name']
    if sha(body) != direct[0]['body_SHA256'] or body.stat().st_size != direct[0]['downloaded_body_bytes']:
        raise ValueError('Original HTTP error-body identity failed')
    if body.read_bytes() != b'error code: 1010\n':
        raise ValueError('Unexpected denied response body')
    public = dict(direct[0])
    public['headers'] = {k.lower():v for k,v in public['headers'].items() if k.lower() in PUBLIC_HEADERS}
    public['headers_policy'] = 'Public diagnostic allowlist; cookies and other headers omitted'
    proof_dir = output / 'sources'
    proof_dir.mkdir(exist_ok=True)
    dump(proof_dir / 'ACQUISITION.json', [public])
    shutil.copyfile(body, proof_dir / body.name)
    web_dir = output / 'web-snapshots'
    web_dir.mkdir(exist_ok=True)
    sources = []
    for path in sorted((evidence / 'web-snapshots').glob('*.txt')):
        metadata = json.loads(path.read_text().splitlines()[0])
        if metadata['representation'] != 'WEB_TOOL_RENDERED_TEXT_CACHE_SNAPSHOT_NOT_ORIGINAL_HTML':
            raise ValueError('Unexpected rendered source representation')
        target = web_dir / path.name
        shutil.copyfile(path, target)
        sources.append(dict(path=str(target.relative_to(output)), original_URL=metadata['original_URL'],
            bytes=target.stat().st_size, SHA256=sha(target),
            representation=metadata['representation'], checksum_binds='Preserved rendered snapshot bytes, NOT original CFTC HTML/archive'))
    if len(sources) != 4:
        raise ValueError('Exactly four previously retrieved official source snapshots expected')
    faq = (web_dir / 'cftc-cot-faq.web.txt').read_text()
    schedule = (web_dir / 'cftc-release-schedule.web.txt').read_text()
    fields = (web_dir / 'cftc-legacy-variables.web.txt').read_text()
    history = (web_dir / 'cftc-historical-compressed.web.txt').read_text()
    checks = {
        'general_friday_1530_eastern_uses_previous_tuesday': 'Friday at 3:30 pm Eastern Time (US), using the data from the immediately preceding Tuesday' in faq,
        'holidays_can_change_release_schedule': 'holidays can change the COT release schedule' in faq,
        'historical_release_list_unavailable_beyond_13_months': 'There is not a list of historical release dates' in faq and '13 months of reports' in faq,
        'current_schedule_tentative_2026_only': 'tentative schedule of releases through 2026' in schedule,
        'legacy_all_OI_long_short_field_order': '8 Open Interest (All) 9 Noncommercial Positions-Long (All) 10 Noncommercial Positions-Short (All)' in fields,
        'contract_units_field_documented': '126 Contract Units' in fields,
        'weekly_change_long_short_fields_documented': '39 Change in Noncommercial-Long (All) 40 Change in Noncommercial-Short (All)' in fields,
        'legacy_futures_only_years_listed': 'Futures Only Reports:' in history and all(str(y) in history for y in (2021,2022,2023,2024)),
    }
    if not all(checks.values()):
        raise ValueError('A declared primary-source finding is not supported by preserved text')
    left, right = date(2021,1,1), date(2024,7,1)
    days = [left + timedelta(days=i) for i in range((right-left).days)]
    # Daily decision dates are requested-domain placeholders, not invented COT observations.
    exclusion_path = output / 'DAILY_EXCLUSIONS.csv'
    with exclusion_path.open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['decision_UTC','eligible','feature_value','reason'])
        for day in days:
            writer.writerow([day.isoformat()+'T00:00:00Z',False,'','OFFICIAL_ARCHIVE_NOT_ACQUIRED;HISTORICAL_RELEASE_TIME_NOT_VERIFIED'])
    field_map = [
        (1,'Market and Exchange Names','Must verify all observed names match the same CME Bitcoin product'),
        (3,'As of Date in Form YYYY-MM-DD','Position observation date; never the publication timestamp'),
        (4,'CFTC Contract Market Code','Requested exact text 133741; actual historical rows not acquired'),
        (8,'Open Interest (All)','Count of all outstanding contracts, conditional on per-row Contract Units confirmation'),
        (9,'Noncommercial Positions-Long (All)','Long noncommercial contract positions; exclude spreading and trader-count columns'),
        (10,'Noncommercial Positions-Short (All)','Short noncommercial contract positions; exclude spreading and trader-count columns'),
        (39,'Change in Noncommercial-Long (All)','Independent cross-check against prior observed consecutive report'),
        (40,'Change in Noncommercial-Short (All)','Independent cross-check against prior observed consecutive report'),
        (126,'Contract Units','Actual Bitcoin units/continuity NOT_VERIFIED without original reports')]
    result = dict(schema='CFTC_BTC_LEGACY_POSITIONING_FEASIBILITY_PARTIAL_V1',
        status='NO_GO_OFFICIAL_ARCHIVE_ACCESS_DENIED_AND_HISTORICAL_RELEASE_CLOCK_UNVERIFIED',
        created_UTC=datetime.now(timezone.utc).isoformat(), requested_contract_code='133741',
        report_family='Legacy Futures Only', interval_UTC_start_inclusive=str(left), interval_UTC_end_exclusive=str(right),
        official_download_budget_bytes=30*1024*1024, direct_official_body_bytes=public['downloaded_body_bytes'],
        direct_attempts=1, original_market_archives_downloaded=0, no_access_bypass=True,
        primary_source_metadata_checks=checks,
        verified_schema_field_descriptions=[dict(one_based_field_number=n,official_description=d,interpretation_or_required_check=c) for n,d,c in field_map],
        feature_proposal='((noncommercial_short_t - noncommercial_long_t) - (noncommercial_short_previous_week - noncommercial_long_previous_week)) / total_open_interest_t',
        feature_formula_status='Explicit reading of supplied proposal; NOT_COMPUTED; current OI denominator. No claimed paper reproduction.',
        feature_scope='CME product trader-category positioning, not retail identity and not crypto-wide positioning',
        release_rule='First daily 00:00 UTC decision strictly after verified publication timestamp plus 48 hours; neither Tuesday observation dates nor a synthetic Friday calendar qualify.',
        release_dependencies='Both current and prior-week values must have source-supported availability. Require consecutive observed report weeks and verified contract/units continuity. Exclude unknown releases rather than forward-fill.',
        actual_contract_continuity='UNKNOWN_NOT_ASSESSED_NO_ORIGINAL_ARCHIVES',
        actual_CME_Bitcoin_units='UNKNOWN_NOT_VERIFIED', actual_CSV_headers='UNKNOWN_NOT_VERIFIED_SCHEMA_DOCUMENTATION_ONLY',
        observed_historical_report_rows=0, missing_reports='UNKNOWN_NOT_ASSESSED_NOT_ZERO',
        historical_publication_mapping='NOT_ESTABLISHED_2021_THROUGH_JUNE2024',
        historical_exceptions_and_delays='NOT_ESTABLISHED_NO_STANDARD_CALENDAR_IMPUTATION',
        daily_decisions_in_requested_domain=len(days), eligible_daily_decisions=0,
        exclusion_file=dict(path=exclusion_path.name,SHA256=sha(exclusion_path)),
        crisis_coverage=[dict(name='Terra 2022',status='NO_GO_PUBLICATION_AND_RAW_REPORT_EVIDENCE_UNVERIFIED'),
                        dict(name='FTX 2022',status='NO_GO_PUBLICATION_AND_RAW_REPORT_EVIDENCE_UNVERIFIED')],
        four_historical_folds_status='NO_GO_FOR_ALL_FOLDS_IN_REQUESTED_DOMAIN; not independently relabeled usable',
        original_archive_checksums='UNAVAILABLE_NO_ORIGINAL_ARCHIVE_BYTES',
        snapshot_sources=sources, exact_denial=dict(URL=public['url'],HTTP_status=403,
            body='error code: 1010',body_bytes=public['downloaded_body_bytes'],body_SHA256=public['body_SHA256']),
        paper=dict(DOI='10.1016/j.jbef.2023.100812',status='NOT_RETRIEVED_NOT_REPRODUCED_ALIGNMENT_AND_PERFORMANCE_NOT_ADOPTED'),
        model_fits=0,parameter_tuning=0,backtests=0,trading=0,
        reopen_requirements=['Lawfully reachable official original archive bytes (or existing source-bound cache) for 2021–June2024',
            'Exact CME product/code/units continuity and report-gap audit',
            'Source-supported historical release timestamps and exceptions; date-only evidence requires an explicit conservative timestamp upper bound',
            'Apply strict release+48h daily eligibility and test chronology before any fit'])
    dump(output / 'RESULT.json', result)
    print(json.dumps({k:result[k] for k in ('status','direct_attempts','direct_official_body_bytes','original_market_archives_downloaded','daily_decisions_in_requested_domain','eligible_daily_decisions','missing_reports')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.evidence,args.output)
