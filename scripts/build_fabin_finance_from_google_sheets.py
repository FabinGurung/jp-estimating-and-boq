#!/usr/bin/env python3
"""Read current Fabin Gurung 8-tab human-owned Sheet, publish unapproved PROJECT AGGREGATES only.
This is a read-only adapter: no source writes, no normalized worksheets required.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "fabin-payments-public.json"
LIVE_TITLE = "JP Cost Estimation — Payments — Fabin Gurung — LIVE v0.7"
PROJECT_TABS = [
    "14_Bishal Paija", "31_Sharada Adhikari", "09_Prithivi Mandi",
    "14_Kharika Poudel", "13_Hari Baral", "04_Basketball Project"
]
RANGES = {"Total": "A1:E20", "00_SYSTEM_MEMORY": "A1:E150"}
RANGES.update({tab: "A1:E900" for tab in PROJECT_TABS})
EPSILON = Decimal("0.01")


class SourceError(Exception):
    pass


def strcell(row, i):
    return str(row[i]).strip() if i < len(row) and row[i] is not None else ""


def num(value):
    if value is None or value == "":
        raise SourceError("MISSING_SOURCE_AMOUNT")
    s = str(value).replace(",", "").replace("NPR", "").strip()
    try:
        x = Decimal(s)
    except InvalidOperation:
        raise SourceError("INVALID_SOURCE_AMOUNT") from None
    if not x.is_finite():
        raise SourceError("INVALID_SOURCE_AMOUNT")
    return x


def read_project(tab, values):
    """Discover every date/amount mini-table in the existing human sheet.
    The source marks its subtotal as '▲ Total'. Never edit source layout.
    """
    groups = []
    group_names = set()
    events = 0
    grand = None
    for i, row in enumerate(values):
        if "master total" in strcell(row, 0).casefold():
            if grand is not None:
                raise SourceError("DUPLICATE_PROJECT_TOTAL")
            grand = num(strcell(row, 2))
        if [strcell(row, k).casefold() for k in (0, 1, 2)] != ["time", "date", "amount"]:
            continue
        if i == 0:
            raise SourceError("MISSING_VENDOR_HEADER")
        group_name = strcell(values[i-1], 0)
        if not group_name or group_name.casefold() in group_names:
            raise SourceError("DUPLICATE_OR_EMPTY_PARTY_SECTION")
        group_names.add(group_name.casefold())
        sum_values = Decimal("0")
        count = 0
        end = None
        for j in range(i + 1, len(values)):
            payment = values[j]
            mark = strcell(payment, 0)
            if "total" in mark.casefold() and "▲" in mark:
                end = j
                break
            if strcell(payment, 2):
                if not strcell(payment, 1):
                    raise SourceError("SOURCE_AMOUNT_WITHOUT_DATE")
                sum_values += num(strcell(payment, 2))
                count += 1
        if end is None:
            raise SourceError("MISSING_VENDOR_SUBTOTAL")
        declared = num(strcell(values[end], 2))
        if abs(sum_values - declared) > EPSILON:
            raise SourceError("VENDOR_DETAIL_SUBTOTAL_DIFFERENCE")
        groups.append(declared)
        events += count
    if not groups or grand is None:
        raise SourceError("NO_PROJECT_GROUPS_OR_TOTAL")
    total = sum(groups, Decimal("0"))
    if abs(total - grand) > EPSILON:
        raise SourceError("PROJECT_SECTIONS_DO_NOT_RECONCILE")
    return {"grand": grand, "sectionTotal": total, "sections": len(groups), "events": events}


def derive(sheets, now=None):
    expected = set(RANGES)
    if not expected.issubset(sheets):
        raise SourceError("MISSING_8TAB_SOURCE")
    total_rows = sheets["Total"]
    if not total_rows or [strcell(total_rows[0], k) for k in range(5)] != ["Project", "Amount", "QR", "Discount", "Company"]:
        raise SourceError("TOTAL_HEADER_DRIFT")
    active = {strcell(row, 0): row for row in total_rows[1:] if strcell(row, 0) and strcell(row, 0) != "Total"}
    if set(active) != set(PROJECT_TABS[:-1]):
        raise SourceError("FIVE_PROJECT_SCOPE_CHANGED")
    declared_row = next((r for r in total_rows if strcell(r, 0) == "Total"), None)
    if declared_row is None:
        raise SourceError("SOURCE_GRAND_TOTAL_MISSING")
    source_total = num(strcell(declared_row, 1))
    five_sum = Decimal("0")
    detail_total = Decimal("0")
    events = 0
    sections = 0
    public = []
    for tab in PROJECT_TABS:
        project = read_project(tab, sheets[tab])
        events += project["events"]
        sections += project["sections"]
        if tab == "04_Basketball Project":
            continue  # recorded separately; excluded due to Prithivi overlap
        row = active[tab]
        declared = num(strcell(row, 1))
        if abs(project["grand"] - declared) > EPSILON:
            raise SourceError("PROJECT_SOURCE_SUMMARY_DIFFERENCE")
        delta = project["sectionTotal"] - declared
        five_sum += declared
        detail_total += project["sectionTotal"]
        public.append({
            "sourceProject": tab,
            "companyAsRecorded": strcell(row, 4),
            "sourceAmountNpr": float(declared),
            "normalizedEntriesNpr": float(project["sectionTotal"]),
            "differenceNpr": float(Decimal("0") if abs(delta) <= EPSILON else delta),
            "entryCount": project["events"],
            "reconciliation": "ARITHMETIC_MATCH_ONLY" if abs(delta) <= EPSILON else "SOURCE_TOTAL_CONFLICT",
            "approval": "NOT_VERIFIED",
        })
    if abs(five_sum - source_total) > EPSILON:
        raise SourceError("FIVE_PROJECT_TOTAL_CONFLICT")
    if events < 1 or sections < 1:
        raise SourceError("EMPTY_SOURCE")
    timestamp = now or datetime.now(timezone.utc)
    return {
        "schema": "jp.fabin-payments.source-aggregate.v1",
        "sourceVersion": "v0.7",
        "normalizedEventVersion": "native-8tab-adapter",
        "generatedAtUtc": timestamp.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "authenticatedSourceFetch": True,
        "publicationStatus": "SOURCE_REPORTED_NOT_VERIFIED",
        "amountMeaning": "SOURCE_REPORTED_NOT_CERTIFIED_PAID",
        "currency": "NPR",
        "sourceProjectCount": 5,
        "sourceDeclaredGrandTotalNpr": float(source_total),
        "normalizedEventsGrandTotalNpr": float(detail_total),
        "reconciliationDifferenceNpr": float(Decimal("0") if abs(detail_total-source_total) <= EPSILON else detail_total-source_total),
        "sourceEventCount": events,
        "sourcePartySectionCount": sections,
        "reviewQueueIssueCount": 1,  # one unresolved overlapping project-family review; NOT count of historic flags
        "projects": public,
        "exclusions": ["Basketball Project: possible duplicate of 09_Prithivi Mandi; excluded from five-project rollup"],
        "cautions": [
            "All amounts are source-recorded, NOT approved, certified or bank-verified payments.",
            "Basketball/Prithivi potential overlap remains unresolved. Review-issue count is category-level only.",
            "Each human mini-table is validated in place; this adapter does not require or write normalized event tables.",
            "Sub-cent arithmetic display rounding is tolerated up to NPR 0.01, not silently corrected.",
        ],
        "privacy": {"publishedIndividualTransactions": 0, "publishedPartyNames": 0,
                    "publishedRawSourceUrls": 0, "officialProjectIdentityVerified": False},
        "checks": {"sourceAndNormalizedSummaryMatched": abs(detail_total-source_total) <= EPSILON,
                   "allPaymentSourceRowsTraceable": True, "projectSummaryExcludesBasketball": True,
                   "allTransactionsUnapproved": True},
    }


def discover_live(session):
    title = LIVE_TITLE.replace("\\", "\\\\").replace("'", "\\'")
    params = {"q": f"name = '{title}' and trashed = false and mimeType = 'application/vnd.google-apps.spreadsheet'",
              "fields": "nextPageToken,files(id,name,mimeType)", "page_size": 100}
    reply = session.get("https://www.googleapis.com/drive/v3/files", params=params, timeout=45)
    reply.raise_for_status()
    found = reply.json().get("files", [])
    if len(found) != 1 or reply.json().get("nextPageToken") or found[0].get("name") != LIVE_TITLE:
        raise SourceError("UNIQUE_LIVE_SOURCE_NOT_FOUND")
    return found[0]["id"]


def fetch_google():
    try:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/spreadsheets.readonly",
                                                "https://www.googleapis.com/auth/drive.readonly"])
        session = AuthorizedSession(creds)
        source = discover_live(session)
        params = [("ranges", f"'{tab.replace(chr(39), chr(39)*2)}'!{rng}") for tab, rng in RANGES.items()]
        params.append(("valueRenderOption", "UNFORMATTED_VALUE"))
        result = session.get(f"https://sheets.googleapis.com/v4/spreadsheets/{source}/values:batchGet",
                             params=params, timeout=90)
        result.raise_for_status()
        values = result.json().get("valueRanges", [])
        if len(values) != len(RANGES):
            raise SourceError("NOT_ALL_CURRENT_TABS_READ")
        return {name: values[i].get("values", []) for i, name in enumerate(RANGES)}
    except SourceError:
        raise
    except Exception:
        raise SourceError("AUTHENTICATED_FABIN_SOURCE_READ_FAILED") from None


def self_test():
    sample = [["ID", "Name", "Amount"], [1, "Sample", 10], ["▲ Master Total", "Total", 10],
              [], ["Vendor"], ["Time", "Date", "Amount", "Discount", "QR"],
              ["10:00", "2026/01/01", 10], ["▲ Total", "", 10]]
    assert read_project("test", sample)["events"] == 1
    assert read_project("test", sample)["sections"] == 1
    try:
        read_project("test", sample[:-1])
    except SourceError:
        pass
    else:
        raise AssertionError("Missing subtotal must fail")
    print("FABIN NATIVE 8-TAB READ-ONLY SELF TEST PASS")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=OUTPUT)
    p.add_argument("--self-test", action="store_true")
    a=p.parse_args()
    if a.self_test:
        self_test()
        return
    data=derive(fetch_google())
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")
    print("FABIN AUTHENTICATED 8-TAB HUMAN SOURCE PASS; 5 source-only project aggregates; no private rows")


if __name__ == "__main__":
    main()
