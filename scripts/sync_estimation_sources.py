#!/usr/bin/env python3
"""Read the estimating source index, then stage only approved public fields."""
import argparse
from datetime import datetime, timezone
import gzip
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
BBS = {'bbs-slab': 'Slab', 'bbs-beam': 'Beam', 'bbs-stair': 'Staircase', 'bbs-shear': 'Shear wall'}


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


def read_registry(session):
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
        key, _, kind, link, tab, mode, _ = (row + [''] * 7)[:7]
        reference = LOCATOR.fullmatch(link)
        if not re.fullmatch(r'[a-z0-9-]+', key) or key in registry or not reference:
            raise SourceHold('Invalid or duplicate source index entry')
        expected_kind = 'Sheet' if reference[1] == 'spreadsheets' else 'Doc'
        if kind != expected_kind:
            raise SourceHold('Source index type mismatch')
        registry[key] = (reference[2], tab, mode)
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


def sync(site):
    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    credentials, _ = google.auth.default(scopes=[
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/spreadsheets.readonly',
    ])
    with AuthorizedSession(credentials) as session:
        registry = read_registry(session)
        bbs = []
        for key, label in BBS.items():
            file, tab, mode = registry[key]
            if mode != 'Read status' or not re.fullmatch(r'[A-Za-z0-9_]+', tab):
                raise SourceHold('Invalid BBS read contract')
            try:
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
