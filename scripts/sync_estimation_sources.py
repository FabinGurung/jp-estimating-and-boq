#!/usr/bin/env python3
"""Read the estimating source index, then stage only approved public fields."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
INDEX_TITLE = 'JP Estimating and BOQ — Source Index — LIVE'
SHEET_MIME = 'application/vnd.google-apps.spreadsheet'
INDEX_HEADERS = ['Key', 'Source', 'Type', 'Google Drive link', 'Tab', 'Use in publishing', 'Notes']
PDF_HEADERS = ['Kind', 'Record ID', 'Description', 'Unit', 'Parsed value', 'PDF page',
               'PDF row', 'Basis', 'Status', 'Evidence metadata']
INDICATIVE_HEADERS = ['Source Rate ID', 'Category', 'Work / Rate Item', 'Contract Basis',
                      'Low NPR', 'High NPR', 'Unit', 'Measurement Basis / Scope', 'Source Status']
LOCATOR = re.compile(r'https://docs\.google\.com/(spreadsheets|document)/d/([A-Za-z0-9_-]{20,160})/edit(?:\?.*)?')
PRIVATE = re.compile(r'https?://|\b[\w.+-]+@[\w.-]+\.\w+\b|ya29\.|private key|access_token', re.I)
BBS = {'bbs-slab': 'Slab', 'bbs-beam': 'Beam', 'bbs-stair': 'Staircase', 'bbs-shear': 'Shear wall', 'bbs-footing': 'Footing', 'bbs-column': 'Column', 'bbs-water-tank': 'Water Tank'}


class SourceHold(Exception):
    """A source is unavailable or failed its publication checks."""


def get_json(session, url, params, label):
    response = session.get(url, params=params, timeout=65)
    if not response.ok:
        raise SourceHold(f'{label}: HTTP {response.status_code}')
    return response.json()


def sheet_rows(session, file_id, a1, label):
    from urllib.parse import quote
    return get_json(session, f'https://sheets.googleapis.com/v4/spreadsheets/{file_id}/values/{quote(a1, safe="")}',
                    {'valueRenderOption': 'UNFORMATTED_VALUE'}, label).get('values', [])


def read_registry(session, worker_codes=None):
    response = get_json(session, 'https://www.googleapis.com/drive/v3/files', {
        'q': f"name = '{INDEX_TITLE}' and mimeType = '{SHEET_MIME}' and trashed = false",
        'fields': 'nextPageToken,files(id,name)', 'pageSize': 100,
    }, 'Source index discovery')
    files = response.get('files', [])
    if len(files) != 1 or response.get('nextPageToken'):
        raise SourceHold('Expected exactly one estimating source index')
    rows = sheet_rows(session, files[0]['id'], "'Sources'!A:G", 'Source index')
    if not rows or rows[0] != INDEX_HEADERS:
        raise SourceHold('Source index headers changed')
    registry = {}
    for row in rows[1:]:
        if not row:
            continue
        key, title, kind, link, tab, mode, _ = (row + [''] * 7)[:7]
        reference = LOCATOR.fullmatch(link)
        if not re.fullmatch(r'[a-z0-9-]+', key) or key in registry or not reference:
            raise SourceHold('Invalid or duplicate source index entry')
        expected_kind = 'Sheet' if reference[1] == 'spreadsheets' else 'Doc'
        if kind != expected_kind:
            raise SourceHold('Source index type mismatch')
        registry[key] = (reference[2], tab, mode)
        if worker_codes is not None and re.fullmatch(r'w\d{2}', key):
            # Match against private index titles in memory; never publish the names.
            name = re.split(r'\s+[-—–]\s+', title, maxsplit=1)[0]
            if not name.upper().startswith(key.upper()+' '):
                raise SourceHold('Workforce source title code mismatch')
            worker = re.sub(r'\s+', '_', name[len(key)+1:].strip()).casefold()
            if not worker or worker in worker_codes:
                raise SourceHold('Workforce source mapping ambiguous')
            worker_codes[worker] = key.upper()
    return registry


def load_records(path):
    contents = path.read_bytes()
    return json.loads(gzip.decompress(contents) if contents.startswith(b'\x1f\x8b') else contents)


def numeric(value):
    return type(value) in {int, float} and math.isfinite(value)


def publish_pdf_rates(session, workbook, site):
    manifest = json.loads((ROOT / 'data/rate-source-derived.v0.5.15.json').read_text())
    for source in manifest['sources']:
        rows = sheet_rows(session, workbook, f"'{source['id']}'!A:J", source['id'])
        if not rows or rows[0] != PDF_HEADERS:
            raise SourceHold('PDF-derived source tab headers changed')
        observed = {}
        for line in rows[1:]:
            if not line:
                continue
            kind, identity, _, _, value, page, *_ = (line + [None] * 10)[:10]
            key = (kind, identity)
            if kind not in ('entries', 'candidates') or not identity or key in observed:
                raise SourceHold('Invalid or duplicate PDF rate identity')
            # Values API uses an empty string for an interior blank cell.
            observed[key] = (value, None if page == '' else page)
        for kind in ('entries', 'candidates'):
            for path in source[kind]:
                records = load_records(ROOT / path)
                for record in records:
                    cell = observed.pop((kind, record['id']), None)
                    if not cell or cell[1] != record.get('page'):
                        raise SourceHold('A registered PDF observation or page reference is missing')
                    value = cell[0] if cell[0] != '' else None
                    if value is not None and (not numeric(value) or source.get('private_fields_withheld')):
                        raise SourceHold('Invalid or unauthorized public PDF value')
                    record['value'] = value
                serialized = json.dumps(records, ensure_ascii=False, separators=(',', ':')).encode()
                (site / path).write_bytes(gzip.compress(serialized, mtime=0))
        if observed:
            raise SourceHold('New PDF observations require an approved source revision')
    return sum(source['entry_count'] + source['candidate_count'] for source in manifest['sources'])


def publish_indicative(session, source, site):
    file_id, tab, _ = source
    rows = sheet_rows(session, file_id, f"'{tab}'!A:I", 'Indicative rate library')
    if not rows or rows[0] != INDICATIVE_HEADERS:
        raise SourceHold('Indicative rate header mismatch')
    result = []
    ids = set()
    for row in rows[1:]:
        if not row:
            continue
        key, category, item, basis, low, high, unit, _, _ = (row + [''] * 9)[:9]
        if (not isinstance(key, str) or key in ids or not key or not item or not unit
                or not numeric(low) or not numeric(high) or low < 0 or high < low
                or any(not isinstance(text, str) or PRIVATE.search(text) for text in (category, item, basis, unit))):
            raise SourceHold('Indicative source contains an invalid public rate row')
        ids.add(key)
        result.append({'category': category, 'item': item, 'basis': basis, 'lowNpr': low,
                       'highNpr': high, 'unit': unit})
    if not result:
        raise SourceHold('The indicative rate library is empty')
    write_json(site / 'data/estimating-indicative-rates.json', result)
    return len(result)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def read_public_guidance(session, file_id):
    response = session.get(f'https://www.googleapis.com/drive/v3/files/{file_id}/export',
                           params={'mimeType': 'text/plain'}, timeout=30)
    if not response.ok:
        raise SourceHold(f'Publishing guide export: HTTP {response.status_code}')
    guidance = [line.removeprefix('[PUBLIC] ').strip() for line in response.text.splitlines()
                if line.startswith('[PUBLIC] ')]
    if not guidance or any(not line or len(line) > 400 or PRIVATE.search(line) for line in guidance):
        raise SourceHold('Public publishing guide paragraphs failed validation')
    return guidance


# 24 November 2026: user-authorized workbook navigation only.
# Never copy private worksheet titles, cells, workforce names or source notes into this directory.
# The existing authenticated Source Index remains the authority for the approved keys.
APPROVED_WORKBOOK_ID_DIGEST = 'b6a753355c721ddb9b3014afe8ed73e8c3fb81611c13d3895946e83e88e38fb9'
WORKBOOK_GROUPS = (
    ('core', 'Rates and finance', (
        ('rate-master', 'Construction Rate Library', 'Rate reference · read on publishing builds', 'Rates'),
        ('pdf-rates', 'PDF Rate Observations', 'Six source families · observations and numeric candidates', 'Rates'),
        ('finance-1', 'Fabin Gurung — Income V000001', 'Manual integrity status · restricted income', 'Finance reader'),
        ('finance-2', 'Contractor Bills — LIVE', 'Manual status · claims not certified', 'Finance reader'),
        ('finance-3', 'Vendor Bills — LIVE', 'Manual status · invoices not certified', 'Finance reader'),
        ('finance-4', 'Fabin Gurung — Payments v0.7', 'Source-reported project payments', 'Finance reader'),
        ('finance-5', 'Krishna Kumar Gupta — Payments V1.1', 'Source reconciliation · restricted original', 'Finance reader'),
        ('funding', 'Project Funding — v1.1', 'Archived historical funding-party attribution', 'Archived'),
    )),
    ('wages', 'Wage List 11 — CLEAN', (
        ('historical-work', 'Work — CLEAN v1.1', 'Clean working register', 'Restricted reference'),
        ('historical-attendance', 'Attendance — CLEAN v1.1', 'Clean working register', 'Restricted reference'),
        ('historical-wage', 'Wage — CLEAN v1.1', 'Clean working register', 'Restricted reference'),
        ('historical-payment', 'Payment — CLEAN v1.1', 'Clean payment register', 'Existing payment reader'),
    )),
    ('workforce', 'Individual workforce workbooks', tuple(
        (f'w{i:02}', f'W{i:02}', 'Money and Goods by Project Site' if i <= 10 else 'Original Attendance by Project Site', 'Restricted field source')
        for i in range(1, 22)
    )),
)


def publish_workbook_links(registry, site):
    groups = []
    seen = set()
    ordered_ids = []
    for key, title, entries in WORKBOOK_GROUPS:
        cards = []
        for source_key, label, detail, expected_mode in entries:
            file_id, _, mode = registry[source_key]
            if mode != expected_mode or not re.fullmatch(r'[A-Za-z0-9_-]{20,160}', file_id) or file_id in seen:
                raise SourceHold('Approved workbook directory contract changed')
            seen.add(file_id)
            ordered_ids.append(file_id)
            if expected_mode == 'Archived':
                continue  # preserve identity in digest, exclude from active links
            cards.append({'key': source_key, 'title': label, 'detail': detail,
                          'url': f'https://docs.google.com/spreadsheets/d/{file_id}/edit'})
        groups.append({'key': key, 'title': title, 'cards': cards})
    if [len(group['cards']) for group in groups] != [7, 4, 21] or len(seen) != 33:
        raise SourceHold('Workbook directory must contain 32 active links and one preserved archived identity')
    if hashlib.sha256('\n'.join(ordered_ids).encode()).hexdigest() != APPROVED_WORKBOOK_ID_DIGEST:
        raise SourceHold('An approved workbook identity changed; review the directory before publishing')
    write_json(site / 'data/estimating-workbook-links.json', {
        'schema': 'jp.estimating.workbook-links.v1',
        'groups': groups,
        'access': 'Google Drive permissions apply; links only; no sharing changes or private rows.',
    })



def publish_quantity_and_projects(session, registry, site):
    # These are registered originals, not engineering approval or procurement authority.
    bbs_ids = [
        ('bbs-slab', 'Slab BBS', '1NWrRJlUr0bZ3TqGE1rYlQDJFaoMK02oqQQvdw0FThL4'),
        ('bbs-beam', 'Beam BBS', '1R66MsXW9hqgH5y7_hFyoXutIHWfgquV2z-TEGq7NDKs'),
        ('bbs-shear', 'Shear Wall BBS', '1qAfo2F7Rm3uXaDERRwslJNyhsi6DmpTN8bmCvqSfY10'),
        ('bbs-stair', 'Staircase BBS', '1KWEGuoa5m96nBHzdsTLMDyw5Y-mn9FHcbMJkBJ7fEiE'),
        ('bbs-footing', 'Footing BBS', '1nYnmXy3_fQp3GY6kZ1WTFd_PJcnF-lB9zCUS6dcoZT8'),
        ('bbs-column', 'Column BBS', '1UocFpIOgzN2_WFoYlE5DPIs29XUvR1rORyCsB0qgzVs'),
        ('bbs-water-tank', 'Water Tank BBS', '1vchKRu-rP_d72d-4E5axpMxf3c6F061PD_MaNsD4uBw'),
    ]
    cards = []
    for key, label, expected in bbs_ids:
        fid, tab, mode = registry[key]
        if fid != expected or mode != 'Read status':
            raise SourceHold('Quantity workbook identity or mode changed')
        cards.append({'key': key, 'title': label, 'detail': 'Working reinforcement and procurement workbook',
                      'url': f'https://docs.google.com/spreadsheets/d/{fid}/edit'})
    fid, _, mode = registry['field-1']
    if fid != '1NvvOD7UUDAvWVnGOC33q2MOy3h6ZDoD1Y2es9l3dpiY' or mode != 'Restricted field source':
        raise SourceHold('Measurement evidence identity changed')
    evidence = {'key': 'field-1', 'title': 'Fishtail Measured Site Work — CLEAN',
                'detail': 'Reviewed measurement entry and summary; original source evidence preserved',
                'url': f'https://docs.google.com/spreadsheets/d/{fid}/edit'}
    concrete_ids = [
        ('concrete-slab', 'Slab Concrete QTO', '1yehFEcGcCw7lJnEnjrVPpXcnGfoqO_iNrWzEeFrvqB8'),
        ('concrete-beam', 'Beam Concrete QTO', '1__mY3cmOFGwhJHDysm-bT4b764-NP5S8kt2D57mtQHg'),
        ('concrete-shear', 'Shear Wall Concrete QTO', '1oJzHRmhKxb3uA6SiUTScz_G2oKkt5bwrU1zL_kQP--Q'),
        ('concrete-stair', 'Staircase Concrete QTO', '1O9Mf89wlQr3gKlyyyZ6AEkfyom4qyMubYaJy08PPQWQ'),
        ('concrete-footing', 'Footing Concrete QTO', '16iAPjM0cEyRTaxT4gu438HpCbtxKHLOLo9AalphMb9o'),
        ('concrete-column', 'Column Concrete QTO', '1DMv_46e-l-TOj4l3qsyAhyRRnQynplmYqrx8gAABp_w'),
        ('concrete-water-tank', 'Water Tank Concrete QTO', '171LITC8Yvtaj4pHTlyUMDmAuKCJZ9l1dgcKY5sWOTHs'),
    ]
    concrete_cards = []
    for key, label, expected in concrete_ids:
        fid, tab, mode = registry[key]
        if fid != expected or tab != '00_PROJECT_SUMMARY' or mode != 'Concrete summary':
            raise SourceHold('Concrete workbook registration changed')
        try:
            summary = sheet_rows(session, fid, "'00_PROJECT_SUMMARY'!A4:C39", label)
            checked = bool(summary and summary[0] == ['Project key','Material / measure','Amount'])
        except SourceHold:
            checked = False
        detail = 'Planning calculator; approved mix required; no purchase release'
        detail += '; summary read verified' if checked else '; summary read not verified'
        concrete_cards.append({'key':key,'title':label,'detail':detail,'url':f'https://docs.google.com/spreadsheets/d/{fid}/edit'})
    material_id, material_tab, material_mode = registry['project-materials']
    if material_id != '1URJiDyCKxC8Y6TzQmhUwSMQByspG0F9Go4uVwck6VUI' or material_tab != '00_PROJECTS' or material_mode != 'Manual summary':
        raise SourceHold('Project materials workbook identity changed')
    material_card = {'key':'project-materials','title':'Project Material & Work Summary','detail':'Values-only manual snapshot; no purchase release','url':f'https://docs.google.com/spreadsheets/d/{material_id}/edit'}
    write_json(site / 'data/quantity-workbook-links.json', {'groups': [
        {'key': 'bbs', 'title': 'Reinforcement BBS', 'cards': cards},
        {'key': 'concrete', 'title': 'Concrete Quantity Takeoff', 'cards': concrete_cards},
        {'key': 'quantity', 'title': 'Work measurement evidence', 'cards': [material_card, evidence]}]})

    def norm(name):
        return ' '.join(re.sub(r'[_-]+', ' ', name.strip().casefold()).split())
    def safe_name(name):
        return isinstance(name, str) and 1 <= len(name) <= 140 and not PRIVATE.search(name) and not any(c in name for c in '<>\n\r')
    groups = {}
    projects = {}
    def add_project(name, org, source, detail=None):
        if not safe_name(name) or not safe_name(org):
            raise SourceHold('Invalid project label')
        k = (org, norm(name))
        if k not in projects:
            p = {'name': name.replace('_', ' '), 'sources': []}
            projects[k] = p
            groups.setdefault(org, []).append(p)
        p = projects[k]
        if not any(s['source'] == source for s in p['sources']):
            row = {'source': source}
            if detail is not None:
                row['detail'] = detail
            p['sources'].append(row)
        return p
    def existing(name):
        found = [(org, p) for (org, n), p in projects.items() if n == norm(name) and org != 'Organization not established']
        return found[0][0] if len(found) == 1 else 'Organization not established'
    def rows(key, tab):
        return sheet_rows(session, registry[key][0], tab, key)
    fab = rows('finance-4', "'Total'!A1:E")
    if not fab or fab[0] != ['Project', 'Amount', 'QR', 'Discount', 'Company']:
        raise SourceHold('Fabin project summary headers changed')
    aliases = {'rohini engineering and consultancy': 'Rohini Engineering and Builders',
               'fishtail buidlers pvt ltd': 'Fishtail Builders',
               'fishtail builders pvt ltd': 'Fishtail Builders'}
    for r in fab[1:]:
        if not r or not r[0] or norm(str(r[0])) == 'total':
            continue
        if len(r) < 5 or not safe_name(r[0]) or not safe_name(r[4]) or not numeric(r[1]):
            raise SourceHold('Invalid Fabin project summary')
        org = aliases.get(norm(r[4]), r[4])
        add_project(r[0], org, 'Fabin Gurung payments', {'recordedNpr': r[1], 'metrics': {'Amount NPR': r[1], 'QR': r[2], 'Discount NPR': r[3]}, 'range': 'Total!A:E', 'state': 'Source-reported payment; not certified'})
    kkg = rows('finance-5', "'Total'!A1:D")
    if not kkg or kkg[0] != ['Project','Amount (NPR)','Discount (NPR)','QR (NPR)']:
        raise SourceHold('KKG project summary headers changed')
    for r in kkg[1:]:
        if not r or not r[0] or norm(str(r[0])) == 'total':
            continue
        if len(r) < 2 or not numeric(r[1]):
            raise SourceHold('Invalid KKG project summary')
        # Existing KKG source adapter explicitly establishes Rohini and Bishal Paija.
        name = '14 Bishal Paija' if norm(r[0]) == 'bishal paija' else r[0]
        add_project(name, 'Rohini Engineering and Builders', 'Krishna Kumar Gupta payments',
                    {'recordedNpr': r[1], 'metrics': {'Amount NPR': r[1], 'Discount NPR': r[2], 'QR': r[3]}, 'range': 'Total!A:D', 'state': 'Source-reported payment; not certified'})

    # Candidate labels are references only. No vendor amounts or contractor names are exported.
    # An exact matching project label can be linked to a recorded organization, not an inferred ownership claim.
    vendor = rows('finance-3', "'VB_MACHINE_REGISTRY'!A448:D480")
    if not vendor or vendor[0] != ['Source Project Label','Candidate Project ID','Project Register Name','Mapping Status']:
        raise SourceHold('Vendor project crosswalk header changed')
    candidates = {}
    for r in vendor[1:]:
        if not r or not r[0]:
            continue
        label, cid, canonical, status = (r + ['']*4)[:4]
        if not safe_name(label) or status not in ('CANDIDATE','UNRESOLVED'):
            raise SourceHold('Invalid vendor crosswalk')
        key = cid if cid else 'unresolved:' + norm(label)
        if cid and not re.fullmatch(r'PRJ-\d{6}', cid):
            raise SourceHold('Invalid candidate ID')
        c = candidates.setdefault(key, {'name': canonical or label, 'labels': set(), 'id': cid})
        c['labels'].add(label)
    # Read the actual human-maintained portfolio rollup; never sum individual bills.
    rollup = rows('finance-3', "'PROJECT_SUMMARY_HUB'!B3:E55")
    if not rollup or rollup[0] != ['Project Code','Project Name','Total Billed (NPR)','Active Vendor Count']:
        raise SourceHold('Vendor executive summary header changed')
    vendor_totals = {}
    for r in rollup[1:]:
        if not r or r[0] == 'Total':
            break
        if len(r) != 4 or not re.fullmatch(r'prj_\d{6}', r[0]) or not numeric(r[2]) or not numeric(r[3]):
            raise SourceHold('Invalid vendor executive summary row')
        cid = r[0].replace('_','-').upper()
        if cid in vendor_totals:
            raise SourceHold('Duplicate vendor project total')
        vendor_totals[cid] = {'Total Billed (NPR)': r[2], 'Active Vendor Count': r[3]}
    candidate_projects = {}
    for c in candidates.values():
        matches = {existing(n) for n in c['labels'] | {c['name']}} - {'Organization not established'}
        org = next(iter(matches)) if len(matches) == 1 else 'Organization not established'
        # Owner correction, 24 November 2026: the nine previously unassigned projects
        # belong to Fishtail Builders. Explicit scope only; future unresolved projects stay unresolved.
        owner_fishtail_ids = {'PRJ-000017', 'PRJ-000021', 'PRJ-000004', 'PRJ-000002',
                              'PRJ-000024', 'PRJ-000023', 'PRJ-000005'}
        owner_fishtail_labels = {'14 hari baral', '20 kriya flagstone'}
        owner_confirmed = (c['id'] in owner_fishtail_ids or
                           (not c['id'] and norm(c['name']) in owner_fishtail_labels))
        if owner_confirmed and org == 'Organization not established':
            org = 'Fishtail Builders'
        # Select a known existing payment project only if there is a unique exact label match.
        exact = [p for (o,n),p in projects.items() if o == org and n in {norm(s) for s in c['labels'] | {c['name']}}]
        name = exact[0]['name'] if len(exact) == 1 else c['name']
        detail = {'state': ('Organization confirmed by owner, 24 Nov 2026; invoice mapping remains provisional' if owner_confirmed else 'Candidate project crosswalk; not invoice approval')}
        if c['id'] in vendor_totals:
            detail.update(metrics=vendor_totals[c['id']], range='PROJECT_SUMMARY_HUB!B:E')
        project = add_project(name, org, 'Vendor Bills', detail)
        if c['id']:
            candidate_projects[c['id']] = (org, project['name'])
    if not set(vendor_totals).issubset(candidate_projects):
        raise SourceHold('Vendor project summary has an unmapped project ID')
    contractor = rows('finance-2', "'CT_PROJECT_SUMMARY'!A1:I")
    if not contractor or contractor[0][:3] != ['Project As Recorded','Candidate Project ID','Contractor Source']:
        raise SourceHold('Contractor summary header changed')
    for r in contractor[1:]:
        if not r or not r[0]:
            continue
        if len(r) < 9 or not numeric(r[3]) or not numeric(r[4]) or not numeric(r[5]) or not numeric(r[6]):
            raise SourceHold('Contractor project summary numeric cells changed')
        org, name = candidate_projects.get(r[1], (existing(r[0]), r[0]))
        add_project(name, org, 'Contractor Bills', {'metrics': {
            'Claimed Amount (NPR, provisional)': r[3], '33-Line Sum (NPR)': r[4],
            'Difference NPR': r[5], 'Primary Work Lines': r[6]},
            'range': 'CT_PROJECT_SUMMARY!A:I', 'state': 'Recorded claim reference; not certified or paid'})
    payload = {'schema': 'jp.estimating.project-directory.v1',
               'readAtUtc': datetime.now(timezone.utc).isoformat(),
               'groups': [{'organization': k, 'projects': v} for k,v in groups.items()],
               'note': 'Separate source-reported records; no combined expenditure or certified amounts.'}
    write_json(site / 'data/estimating-project-directory.json', payload)
    print('Project directory: source-backed organization groups and separate source references:', sum(len(v) for v in groups.values()))



def publish_clean_wages(session, registry, site, codes):
    """Project exact existing Summary cells only, never recalculate wage or payment totals."""
    specs = [
        ('historical-work','Work',['Worker ID','Worker','Work/allocation records','Distinct dates','Compact work'],
         ['Project site','Work/allocation records','Workers'],4),
        ('historical-attendance','Attendance',['Worker ID','Worker','Records','Worked dates','Regular hours recorded','OT hours recorded'],
         ['Project site','Records','Workers','Worked worker-days','Regular hours','OT hours'],5),
        ('historical-wage','Wage',['Worker ID','Worker','Records','Base wage NPR','OT wage NPR','Gross wage NPR'],
         ['Project site','Records','Workers','Base wage NPR','OT wage NPR','Gross wage NPR'],5),
        ('historical-payment','Payment',['Worker ID','Worker','Payment records','Payment NPR'],
         ['Project site','Payment records','Workers','Payment NPR'],3),
    ]
    data = []
    if len(codes) != 21:
        raise SourceHold('Expected 21 unique workforce codes from private Source Index')
    for key, title, headers, site_headers, width in specs:
        rows = sheet_rows(session, registry[key][0], "'Summary'!A1:F250", title+' clean summary')
        if not rows or rows[0][:len(headers)] != headers:
            raise SourceHold('Clean summary header changed: '+title)
        total = [r for r in rows if r and r[0]=='TOTAL']
        if len(total)!=1:
            raise SourceHold('Clean summary TOTAL missing or ambiguous: '+title)
        cells = (total[0]+['']*len(headers))[:len(headers)]
        totals = {h:v for h,v in zip(headers[2:],cells[2:]) if numeric(v)}
        start = next((i for i,r in enumerate(rows) if r and r[0]=='BY PROJECT SITE'),None)
        if start is None or rows[start+1][:len(site_headers)] != site_headers:
            raise SourceHold('Clean project-site summary header changed: '+title)
        sites=[]
        for r in rows[start+2:]:
            if not r or not r[0] or str(r[0]).upper()=='TOTAL' or len(r)<2 or not numeric(r[1]):
                break
            if not isinstance(r[0],str) or PRIVATE.search(r[0]):
                raise SourceHold('Invalid clean site label')
            sites.append((r+['']*len(site_headers))[:len(site_headers)])
        # Only coded worker work/attendance quantities, no personal names or individual pay amounts.
        workers=[]
        if title in ('Work','Attendance'):
            for r in rows[1:]:
                if not r or not r[0] or r[0]=='TOTAL':
                    break
                if str(r[0]).casefold() not in codes:
                    continue
                values = (r+['']*len(headers))[:len(headers)]
                workers.append([codes[str(r[0]).casefold()]]+values[2:4])
        data.append({'key':key,'title':title,'range':'Summary!A:F','totals':totals,
                     'siteHeaders':site_headers,'sites':sites,'workers':workers,
                     'workerHeaders':['Worker code']+headers[2:4] if workers else []})
    write_json(site/'data/clean-wage-summaries.json', {'schema':'jp.clean-wage-summaries.v1',
                'readAtUtc':datetime.now(timezone.utc).isoformat(),'sections':data})


def sync(site):
    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    credentials, _ = google.auth.default(scopes=[
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/spreadsheets.readonly',
    ])
    with AuthorizedSession(credentials) as session:
        worker_codes = {}
        registry = read_registry(session, worker_codes)
        publish_workbook_links(registry, site)
        publish_quantity_and_projects(session, registry, site)
        try:
            publish_clean_wages(session, registry, site, worker_codes)
        except SourceHold as exc:
            print('Optional CLEAN summaries held:', str(exc))
            snapshot = json.loads((ROOT/'data/clean-wage-summary-manual.v1.json').read_text())
            if snapshot.get('schema') != 'jp.clean-wage-summaries.v1' or snapshot.get('sourceMode') != 'MANUAL_CONNECTOR_SNAPSHOT' or len(snapshot.get('sections', [])) != 4:
                raise SourceHold('Invalid manual CLEAN summary snapshot')
            write_json(site/'data/clean-wage-summaries.json', snapshot)
        bbs = []
        for key, label in BBS.items():
            file, tab, mode = registry[key]
            if mode != 'Read status' or not re.fullmatch(r'[A-Za-z0-9_]+', tab):
                raise SourceHold('Invalid BBS read contract')
            try:
                if key == 'bbs-footing':
                    if tab != '00_Order_and_Projects':
                        raise SourceHold('Footing order tab changed')
                    order = sheet_rows(session, file, f"'{tab}'!A1:C11", label)
                    checked = (len(order) == 11 and order[2] == [
                        'Rebar diameter', 'Muutha to order', 'Purchased 12 m rods']
                        and all(len(r) == 3 and numeric(r[0]) and (
                            (r[1] == 'HOLD' and r[2] == 'HOLD') or
                            (numeric(r[1]) and numeric(r[2]) and r[1] >= 0 and r[2] >= 0
                             and int(r[1]) == r[1] and int(r[2]) == r[2]))
                            for r in order[3:]))
                    if not checked:
                        raise SourceHold('Footing procurement table failed schema check')
                elif key == 'bbs-water-tank':
                    if tab != '00_PROJECTS_AND_ORDER':
                        raise SourceHold('Water tank order tab changed')
                    order = sheet_rows(session, file, f"'{tab}'!A4:C12", label)
                    hold = sheet_rows(session, file, f"'{tab}'!A27:C27", label)
                    checked = (len(order) == 9 and order[0] == ['DIAMETER mm', 'MUUTHA', '12 m RODS']
                               and [r[0] for r in order[1:] if r] == [8,10,12,16,20,25,32,7]
                               and all(not any(v not in ('', None) for v in r[1:]) for r in order[1:])
                               and hold == [['RELEASE', 'HOLD', 'NO PURCHASE']])
                    if not checked:
                        raise SourceHold('Water tank hold / blank approved-order schema check failed')
                elif key == 'bbs-column':
                    if tab != '00_PROJECTS_AND_ORDER':
                        raise SourceHold('Column order tab changed')
                    order = sheet_rows(session, file, f"'{tab}'!A4:C12", label)
                    checked = (len(order) == 9 and order[0] == ['Rebar diameter (mm)', 'Muutha', '12 m rods']
                        and [r[0] for r in order[1:] if r] == [8,10,12,16,20,25,32,7]
                        and all(len(r) == 3 and ((r[1] == 'HOLD' and r[2] == 'HOLD') or
                            (numeric(r[1]) and numeric(r[2]) and r[1] >= 0 and r[2] >= 0
                             and int(r[1]) == r[1] and int(r[2]) == r[2])) for r in order[1:]))
                    if not checked:
                        raise SourceHold('Column procurement table failed schema check')
                else:
                    checked = bool(sheet_rows(session, file, f"'{tab}'!A1:J12", label))
            except SourceHold:
                checked = False
            bbs.append({'item': label, 'sourceRead': checked})
        workbook, _, _ = registry['pdf-rates']
        counts = {'registered': len(registry), 'indicativeRates': publish_indicative(session, registry['rate-master'], site),
                  'pdfRateObservations': publish_pdf_rates(session, workbook, site),
                  'restrictedFieldSources': sum(mode == 'Restricted field source' for _, _, mode in registry.values())}
        guidance = read_public_guidance(session, registry['publishing-guide'][0])
    result = {'schema': 'jp.estimating.source-receipt.v1', 'readAtUtc': datetime.now(timezone.utc).isoformat(),
              'counts': counts, 'reinforcement': bbs, 'guidance': guidance}
    write_json(site / 'data/estimating-source-receipt.json', result)
    print('Source index and rate reads verified:', counts, 'BBS reads:', sum(x['sourceRead'] for x in bbs))


if __name__ == '__main__':
    cli = argparse.ArgumentParser()
    cli.add_argument('--site', required=True, type=Path)
    try:
        sync(cli.parse_args().site)
    except (SourceHold, KeyError, ValueError) as exc:
        raise SystemExit(str(exc) if isinstance(exc, SourceHold) else 'Source index or payload failed validation') from None
