#!/usr/bin/env python3
"""Read native consolidated Vendor Bills registry, publish counts only.
No Google Sheets writes. Public output omits all source IDs, bill rows, names and amounts.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
LIVE_TITLE="JP Cost Estimation — Bills — Vendors — LIVE"
OUTPUT=ROOT/"data/vendor-bills-status.v2.json"
SECTIONS={
    "billRows":("SEC_01_BILLS","VB_BILL_RECORDS",22,281,259,True),
    "summaryRows":("SEC_02_SUMMARIES","VB_SOURCE_SUMMARIES",285,394,109,True),
    "comparisonRows":("SEC_03_RECON","VB_RECONCILIATION",398,444,46,False),
    "projectCrosswalkRows":("SEC_04_PRJ_XWALK","VB_PROJECT_CROSSWALK",448,480,32,True),
    "vendorCrosswalkRows":("SEC_05_VND_XWALK","VB_VENDOR_CROSSWALK",484,514,30,True),
    "detailRows":("SEC_06_DETAILS","VB_DETAIL_ROWS",518,1448,930,True),
}

class SourceError(Exception): pass

def value(rows,i,k=0):
    return str(rows[i][k]).strip() if i<len(rows) and k<len(rows[i]) and rows[i][k] is not None else ""

def verify_keys(rows, count, unique=True):
    if len(rows) != count+1 or not value(rows,0):
        raise SourceError("REGISTRY_HEADER_OR_RANGE_DRIFT")
    values=[value(rows,i) for i in range(1,len(rows))]
    if len(values)!=count or any(not v for v in values):
        raise SourceError("REGISTRY_RECORD_COUNT_OR_BLANK_ID")
    if unique and len(set(values))!=count:
        raise SourceError("REGISTRY_DUPLICATE_CANONICAL_ID")
    return count

def derive(dataset,now=None):
    manifest=dataset.get("manifest",[])
    controls={value(manifest,i):value(manifest,i,1) for i in range(len(manifest))}
    version=controls.get("CONTROL_VERSION","")
    if not re.fullmatch(r"V\d{6}",version):
        raise SourceError("SOURCE_CONTROL_VERSION_MISSING")
    if controls.get("UNIFIED_AUDIT_ENGINE")!="VB_MACHINE_REGISTRY" or controls.get("REFRESH_MODE")!="MANUAL_AI_HYBRID":
        raise SourceError("SOURCE_CONTROL_MODE_DRIFT")
    source_tabs=controls.get("ACTIVE_SOURCE_TABS","")
    if not source_tabs.startswith("35 "):
        raise SourceError("ORIGINAL_SOURCE_TAB_DECLARATION_CHANGED")
    directory=dataset.get("directory",[])
    if not directory or [value(directory,0,k) for k in range(5)]!=["SECTION_ID","SECTION_NAME","START_ROW","END_ROW","RECORD_COUNT"]:
        raise SourceError("REGISTRY_SECTION_DIRECTORY_MISSING")
    sections={value([row],0):row for row in directory[1:] if row and value([row],0)}
    out={}
    for field,(section,name,start,end,count,unique) in SECTIONS.items():
        if section not in sections:
            raise SourceError("REGISTRY_MISSING_SECTION")
        row=sections[section]
        if (value([row],0,1)!=name or
            [int(value([row],0,k)) for k in (2,3,4)]!=[start,end,count]):
            raise SourceError("REGISTRY_SECTION_DIRECTORY_DRIFT")
        out[field]=verify_keys(dataset.get(field,[]),count,unique)
    timestamp=now or datetime.now(timezone.utc)
    return {"schema":"jp.vendor-bills-status.v2",
        "sourceMode":"MANUAL_AUTHENTICATED_READ",
        "revision":version,
        "generatedAtUtc":timestamp.isoformat(timespec="seconds").replace("+00:00","Z"),
        "originalSourceTabsDeclared":35,
        "machineRows":sum(out.values()),
        **out,
        "reviewFlags":None,
        "reviewStatus":"NOT_RECOVERABLE_FROM_CURRENT_SIX_SECTION_REGISTRY",
        "financialApproval":"NOT_VERIFIED",
        "privacy":{"transactionRowsPublished":0,"privateSourceUrlsPublished":0,
                   "vendorNamesPublished":0,"projectAmountsPublished":0},
        "cautions":["The old 1,895/509 counts belong to a historical snapshot; current review queue is not available in this six-section registry.",
                    "Counts are current source-structure readbacks, not certified invoices or payments."]}
def discover(session):
    name=LIVE_TITLE.replace("\\","\\\\").replace("'","\\'")
    q=f"name = '{name}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
    r=session.get("https://www.googleapis.com/drive/v3/files",
                  params={"q":q,"pageSize":100,"fields":"nextPageToken,files(id,name,mimeType)"},timeout=45)
    r.raise_for_status()
    data=r.json()
    a=data.get("files",[])
    if len(a)!=1 or data.get("nextPageToken") or a[0].get("name")!=LIVE_TITLE:
        raise SourceError("UNIQUE_CURRENT_VENDOR_SOURCE_NOT_FOUND")
    return a[0]["id"]
def fetch_google():
    try:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        cred,_=google.auth.default(scopes=["https://www.googleapis.com/auth/drive.metadata.readonly","https://www.googleapis.com/auth/spreadsheets.readonly"])
        session=AuthorizedSession(cred)
        source=discover(session)
        ranges=[("manifest","'00_MANIFEST'!A1:B25"),("directory","'VB_MACHINE_REGISTRY'!A4:H10")]
        for field,(_,_,start,end,_,_) in SECTIONS.items():
            ranges.append((field,f"'VB_MACHINE_REGISTRY'!A{start}:A{end}"))
        params=[("ranges",r) for _,r in ranges]+[("valueRenderOption","FORMATTED_VALUE")]
        r=session.get(f"https://sheets.googleapis.com/v4/spreadsheets/{source}/values:batchGet",params=params,timeout=90)
        r.raise_for_status()
        blocks=r.json().get("valueRanges",[])
        if len(blocks)!=len(ranges):raise SourceError("MISSING_SOURCE_SECTION")
        return {name:blocks[i].get("values",[]) for i,(name,_) in enumerate(ranges)}
    except SourceError:raise
    except Exception:
        raise SourceError("AUTHENTICATED_VENDOR_READ_FAILED") from None

def self_test():
    assert verify_keys([["Bill Record ID"],["A"],["B"]],2)==2
    assert verify_keys([["Vendor Key"],["A"],["A"]],2,unique=False)==2
    try:verify_keys([["ID"],["A"],["A"]],2)
    except SourceError:pass
    else:raise AssertionError("DUPLICATE_ID_ACCEPTED")
    assert sum(s[4] for s in SECTIONS.values())==1406
    print("VENDOR CONSOLIDATED V2 READ-ONLY PARSER SELF-TEST PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--output",type=Path,default=OUTPUT)
    args=p.parse_args()
    if args.self_test:self_test();return
    out=derive(fetch_google())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print("VENDOR V2 CURRENT SIX-SECTION AUTHENTICATED SOURCE READ PASS; privacy preserved")

if __name__=="__main__":
    main()
