#!/usr/bin/env python3
"""Read-only, aggregate-only public status for the A9 Contractor Bills LIVE register.

Google Drive owns all original claims, measurements, historical rows and review evidence.
Only an explicitly dispatched authenticated Actions workflow may read the LIVE Sheet.
Neither this script nor GitHub Pages writes back to Google Sheets.
"""
import argparse
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/contractor-bills-status.v1.json"
SOURCE_TABS = (
    "Hari_Chaudhari", "Khem_Bahadur_Thapa",
    "14_Bishal paija (2)", "14_Bishal paija (3)", "13_hari_baral", "Sheet1",
)
READ_RANGES = {
    "00_MANIFEST": "A1:C30",
    "CT_CLAIM_REGISTER": "A1:L50",
    "CT_WORK_ITEMS": "A1:N100",
    "CT_HISTORICAL_ROWS": "A1:L110",
    "CT_RECONCILIATION": "A1:J60",
    "CT_REVIEW_QUEUE": "A1:H100",
    "CT_SOURCE_INDEX": "A1:G150",
    "Hari_Chaudhari": "A1:E40",
    "Khem_Bahadur_Thapa": "A1:D21",
}
COUNT_KEYS = ("sourceTabs", "sourceRows", "claimRows", "workRows", "historicalRows",
              "comparisonRows", "reviewFlags", "approvedClaims")
PUBLIC_FIELDS = {"schema", "sourceMode", "revision", "normalizedDataRevision", *COUNT_KEYS}


def amount(value):
    try:
        return Decimal(str(value or "0").replace(",", "").strip())
    except InvalidOperation as exc:
        raise ValueError("SOURCE_NUMBER") from exc


def valid(payload):
    if set(payload) != PUBLIC_FIELDS or payload["schema"] != "jp.contractor-bills-status.v1":
        raise ValueError("PUBLIC_SCHEMA")
    if payload["sourceMode"] not in ("VERIFIED_SNAPSHOT", "MANUAL_AUTHENTICATED_READ"):
        raise ValueError("SOURCE_MODE")
    for name in ("revision", "normalizedDataRevision"):
        if not isinstance(payload.get(name), str) or not re.fullmatch(r"V[0-9]{6}", payload[name]):
            raise ValueError("CONTROL_VERSION")
    for name in COUNT_KEYS:
        if type(payload[name]) is not int or payload[name] < 0:
            raise ValueError("PUBLIC_COUNT")
    if (payload["sourceTabs"] < 1 or payload["sourceRows"] < payload["workRows"]
            or payload["approvedClaims"] > payload["claimRows"]):
        raise ValueError("SOURCE_RECONCILIATION")
    return payload


def populated(sheet, header):
    rows = sheet or []
    if not rows or not rows[0] or rows[0][0] != header:
        raise ValueError("SOURCE_HEADER")
    records = [row for row in rows[1:] if row and row[0]]
    if len({row[0] for row in records}) != len(records):
        raise ValueError("DUPLICATE_RECORD_ID")
    return records


def derive(sheets):
    manifest_rows = sheets["00_MANIFEST"]
    if not manifest_rows or manifest_rows[0][:2] != ["Field", "Value"]:
        raise ValueError("SOURCE_MANIFEST")
    manifest = {r[0]: r[1] for r in manifest_rows[1:] if len(r) > 1 and r[0]}
    if manifest.get("LIVE_REGISTER_STATUS") != "MANUAL_FIRST_UNAPPROVED":
        raise ValueError("SOURCE_GOVERNANCE")
    if manifest.get("FINANCIAL_APPROVAL") != "NOT_APPROVED":
        raise ValueError("SOURCE_FINANCIAL_STATUS")
    if any(name not in manifest.get("SOURCE_DATA_TABS", "") for name in
           ("Hari_Chaudhari", "Khem_Bahadur_Thapa", "14_Bishal paija (2)/(3)",
            "13_hari_baral", "Sheet1")):
        raise ValueError("SOURCE_TAB_CONTRACT")

    claims = populated(sheets["CT_CLAIM_REGISTER"], "Claim ID")
    works = populated(sheets["CT_WORK_ITEMS"], "Work Item ID")
    historic = populated(sheets["CT_HISTORICAL_ROWS"], "Historical Row ID")
    reconcile = populated(sheets["CT_RECONCILIATION"], "Comparison ID")
    reviews = populated(sheets["CT_REVIEW_QUEUE"], "Issue ID")
    indexed = populated(sheets["CT_SOURCE_INDEX"], "Source Row ID")
    ids = {row[0]: row for row in indexed}
    claim_ids = {r[0] for r in claims}
    if any(len(r) < 14 or r[1] not in claim_ids or r[13] != "REVIEW_REQUIRED" for r in works):
        raise ValueError("WORK_LINK_APPROVAL")
    if any(len(r) < 12 or r[10] != "NO" for r in historic):
        raise ValueError("HISTORICAL_DOUBLE_COUNT")
    if any(len(r) < 8 or r[6] not in ("OPEN", "IN_REVIEW", "RESOLVED_WITH_EVIDENCE",
                                      "REJECTED_WITH_EVIDENCE") for r in reviews):
        raise ValueError("REVIEW_STATUS")
    for r in works:
        original = r[11].split(":")[0]
        source_row = int(re.search(r"[0-9]+$", original).group(0)) if re.search(r"[0-9]+$", original) else None
        key = f"CTSI-1198426674-{source_row}"
        if (source_row is None or key not in ids or ids[key][1] != r[10]
                or ids[key][2] != r[11] or ids[key][4] != r[0]):
            raise ValueError("WORK_SOURCE_POINTER")
    for r in historic:
        if len(r) < 9 or r[0].replace("CTH-", "CTSI-", 1) not in ids:
            raise ValueError("HISTORICAL_SOURCE_POINTER")
    if any(len(r) < 7 or amount(r[6]) != 0 for r in reconcile):
        raise ValueError("SOURCE_RECONCILIATION_DIFFERENCE")
    if len(claims) != 2 or len(works) < 1:
        raise ValueError("SOURCE_CLAIM_GRAIN")
    source = sheets["Hari_Chaudhari"]
    if len(source) < 40 or len(source[1]) < 2 or len(source[39]) < 3:
        raise ValueError("PRIMARY_SOURCE_RANGE")
    primary_amount = sum((amount(r[7]) for r in works), Decimal("0"))
    if (primary_amount != amount(claims[0][5]) or primary_amount != amount(source[1][1])
            or primary_amount != amount(source[39][2])):
        raise ValueError("PRIMARY_SOURCE_AMOUNT")
    if amount(claims[1][5]) != 0:
        raise ValueError("SECONDARY_SOURCE_AMOUNT")
    if not sheets["Khem_Bahadur_Thapa"] or amount(sheets["Khem_Bahadur_Thapa"][1][1]) != 0:
        raise ValueError("SECONDARY_SOURCE_RANGE")
    result = {
        "schema": "jp.contractor-bills-status.v1",
        "sourceMode": "MANUAL_AUTHENTICATED_READ",
        "revision": manifest.get("CONTROL_VERSION"),
        "normalizedDataRevision": manifest.get("NORMALIZED_DATA_VERSION"),
        "sourceTabs": len(SOURCE_TABS),
        "sourceRows": len(indexed),
        "claimRows": len(claims),
        "workRows": len(works),
        "historicalRows": len(historic),
        "comparisonRows": len(reconcile),
        "reviewFlags": sum(r[6] in ("OPEN", "IN_REVIEW") for r in reviews),
        "approvedClaims": sum(r[10] == "APPROVED_WITH_EVIDENCE" for r in claims),
    }
    return valid(result)


def read_live(source_id):
    import google.auth
    from google.auth.transport.requests import AuthorizedSession
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{source_id}/values:batchGet"
    params = [("ranges", f"'{name}'!{bounds}") for name, bounds in READ_RANGES.items()]
    session = AuthorizedSession(credentials)
    reply = session.get(url, params=params, timeout=30)
    if not reply.ok:
        raise RuntimeError("SHEETS_READ_UNAVAILABLE")
    values = reply.json().get("valueRanges", [])
    if len(values) != len(READ_RANGES):
        raise ValueError("SOURCE_TAB_COUNT")
    return {name: v.get("values", []) for name, v in zip(READ_RANGES, values)}


def self_test():
    sample = json.loads(SNAPSHOT.read_text())
    valid(sample)
    if sample["sourceMode"] != "VERIFIED_SNAPSHOT":
        raise ValueError("UNSAFE_STATIC_SOURCE")
    if sample["revision"] != "V000002" or sample["normalizedDataRevision"] != "V000001":
        raise ValueError("STATIC_VERSION")
    expected = dict(sourceTabs=6, sourceRows=80, claimRows=2, workRows=33,
                    historicalRows=34, comparisonRows=5, reviewFlags=16, approvedClaims=0)
    if any(sample.get(key) != value for key, value in expected.items()):
        raise ValueError("STATIC_COUNTS")
    for malformed in (dict(sample, privatePaymentId="PRIVATE"), dict(sample, reviewFlags=True),
                      dict(sample, sourceRows=0)):
        try:
            valid(malformed)
        except ValueError:
            pass
        else:
            raise ValueError("TEST_EXPECTED_FAILURE")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    self_test()
    if args.check:
        valid(json.loads(SNAPSHOT.read_text()))
    if args.output:
        source_id = os.environ.get("JP_CONTRACTOR_BILLS_SHEET_ID", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{20,}", source_id):
            raise ValueError("SOURCE_CONFIGURATION")
        data = derive(read_live(source_id))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Never print provider URLs, spreadsheet IDs, private rows or financial amounts.
        print(f"Contractor Bills validation failed ({type(exc).__name__}).", file=sys.stderr)
        sys.exit(1)
