#!/usr/bin/env python3
"""Private Fabin income native Google Sheet -> read-only source-integrity STATUS.
No income amounts, names, transactions, account IDs, original OneDrive URL in public output.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
import json
from pathlib import Path

LIVE_TITLE="JP Cost Estimation — Income — Fabin Gurung — LIVE V000001"
OUTPUT=Path(__file__).resolve().parents[1]/"data/income-register-status.v1.json"
class SourceError(Exception):pass
def val(row,i):
    return str(row[i]).strip() if i<len(row) and row[i] is not None else ""
def amount(raw):
    if not raw:raise SourceError("INCOME_BLANK_AMOUNT")
    try:x=Decimal(str(raw).replace(",","").replace("NPR",""))
    except InvalidOperation:raise SourceError("INCOME_INVALID_AMOUNT") from None
    if not x.is_finite():raise SourceError("INCOME_INVALID_AMOUNT")
    return x
def derive(sheet,custody,now=None):
    if not sheet or [val(sheet[0],i) for i in range(5)]!=["Level_01_Summary","Name","Amount","QR","Discount"]:
        raise SourceError("INCOME_SUMMARY_HEADER_DRIFT")
    if not custody or "SOURCE CUSTODY" not in val(custody[0],0):
        raise SourceError("SOURCE_CUSTODY_MISSING")
    groups={}
    grand=None
    for row in sheet[1:]:
        if val(row,0)=="Total" and grand is None:
            grand=amount(val(row,2));break
        if val(row,0).isdecimal() and val(row,1):
            if val(row,1) in groups:raise SourceError("INCOME_DUPLICATE_GROUP")
            groups[val(row,1)]=amount(val(row,2))
    if not groups or grand is None:raise SourceError("INCOME_SUMMARY_EMPTY")
    detailed={};events=0
    for i,row in enumerate(sheet):
        if val(row,1)!="Date" or val(row,2)!="Amount" or not val(row,0).startswith("Level_02_"):
            continue
        group=val(row,0)
        if group in detailed:raise SourceError("INCOME_DUPLICATE_DETAIL_GROUP")
        subtotal=Decimal("0");count=0;closing=False
        for k in range(i+1,len(sheet)):
            r=sheet[k]
            if val(r,0)=="Total":
                if abs(subtotal-amount(val(r,2)))>Decimal("0.01"):
                    raise SourceError("INCOME_SECTION_TOTAL_CONFLICT")
                closing=True;break
            if val(r,2):
                if not val(r,1):raise SourceError("INCOME_AMOUNT_WITHOUT_DATE")
                subtotal+=amount(val(r,2));count+=1
        if not closing:raise SourceError("INCOME_SECTION_WITHOUT_TOTAL")
        detailed[group]=subtotal;events+=count
    if set(groups)!=set(detailed):raise SourceError("INCOME_SUMMARY_GROUP_COVERAGE")
    if any(abs(groups[k]-detailed[k])>Decimal("0.01") for k in groups):
        raise SourceError("INCOME_SUMMARY_DETAIL_CONFLICT")
    if abs(sum(groups.values(),Decimal("0"))-grand)>Decimal("0.01"):
        raise SourceError("INCOME_GRAND_TOTAL_CONFLICT")
    timestamp=now or datetime.now(timezone.utc)
    return {"schema":"jp.fabin-income.status.v1","sourceMode":"MANUAL_AUTHENTICATED_READ",
        "sourceVersion":"V000001","generatedAtUtc":timestamp.isoformat(timespec="seconds").replace("+00:00","Z"),
        "sourceTabCount":2,"incomeGroupsChecked":len(groups),"sourceIncomeEntriesChecked":events,
        "sourceArithmeticReconciled":True,"originalExcelFilterDifference":"RESOLVED_SOURCE_FILTER_PRESENTATION",
        "financialCertification":"NOT_VERIFIED","oneDriveSync":False,
        "privacy":{"publishedEntryRows":0,"publishedIncomeAmounts":0,"publishedSourceLinks":0,
                   "publishedPartyNames":0}}
def discover(session):
    name=LIVE_TITLE.replace("\\","\\\\").replace("'","\\'")
    q=f"name = '{name}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
    r=session.get("https://www.googleapis.com/drive/v3/files",params={"q":q,"pageSize":100,"fields":"nextPageToken,files(id,name,mimeType)"},timeout=45)
    r.raise_for_status()
    d=r.json();files=d.get("files",[])
    if len(files)!=1 or d.get("nextPageToken") or files[0].get("name")!=LIVE_TITLE:raise SourceError("UNIQUE_INCOME_LIVE_SOURCE_NOT_FOUND")
    return files[0]["id"]
def fetch_google():
    try:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        creds,_=google.auth.default(scopes=["https://www.googleapis.com/auth/drive.metadata.readonly",
                                            "https://www.googleapis.com/auth/spreadsheets.readonly"])
        s=AuthorizedSession(creds);source=discover(s)
        rr=s.get(f"https://sheets.googleapis.com/v4/spreadsheets/{source}/values:batchGet",
          params=[("ranges","'14_bishal_paija'!A1:E250"),("ranges","'00_SOURCE_CUSTODY'!A1:F25"),("valueRenderOption","UNFORMATTED_VALUE")],timeout=90)
        rr.raise_for_status();blocks=rr.json().get("valueRanges",[])
        if len(blocks)!=2:raise SourceError("MISSING_INCOME_TABS")
        return [x.get("values",[]) for x in blocks]
    except SourceError:raise
    except Exception:raise SourceError("AUTHENTICATED_INCOME_READ_FAILED") from None

def self_test():
    rows=[["Level_01_Summary","Name","Amount","QR","Discount"],
      [1,"Level_02_One",100,0,0],["Total","",100,0,0],[],
      ["Level_02_One","Date","Amount","QR","Discount"],["10:00","2026/01/02",100],["Total","",100,0,0]]
    custody=[["SOURCE CUSTODY — ESTIMATE"]]
    x=derive(rows,custody);assert x["incomeGroupsChecked"]==1 and x["sourceIncomeEntriesChecked"]==1
    try:derive(rows[:5],custody)
    except SourceError:pass
    else:raise AssertionError("MISSING_DETAIL_ACCEPTED")
    print("INCOME READ-ONLY STATUS SELF-TEST PASS")

def main():
    p=argparse.ArgumentParser();p.add_argument("--self-test",action="store_true")
    p.add_argument("--output",type=Path,default=OUTPUT);a=p.parse_args()
    if a.self_test:self_test();return
    income,custody=fetch_google();out=derive(income,custody)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print("INCOME PRIVATE TWO-TAB GOOGLE READ PASSED; PUBLIC STATUS WITHOUT AMOUNTS")
if __name__=="__main__":main()
