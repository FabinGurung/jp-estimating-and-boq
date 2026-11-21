#!/usr/bin/env python3
"""Read the exact LIVE KKG V1.1 three-tab Google Sheet with existing WIF identity.

Source-only finance figures: no spreadsheet writes, no private file IDs in Git,
no public stable Entry IDs, no certification of bank or tax payments.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "finance-public-snapshot.json"
LIVE_TITLE = "JP Cost Estimation — Payments — Krishna Kumar Gupta — LIVE V1.1"
TAB_NAMES = ("Total", "Bishal Paija", "00_SYSTEM_MEMORY")
SOURCE_VERSION = "V1.1 / V000002"
DATE = re.compile(r"^\d{4}(?:_\d{2}_\d{2}|-\d{2}-\d{2}|/\d{2}/\d{2})$")
HEADING = re.compile(r"^VENDOR\s+(\d+)\s+·\s+(.+)$")
BAD = {"#REF!", "#N/A", "#VALUE!", "#ERROR!", "#DIV/0!", "#NAME?", "#NUM!"}

class SourceError(Exception):
    pass

def cell(row, n):
    return str(row[n] if n < len(row) and row[n] is not None else "").strip()

def decimal(value, required=False):
    raw = str(value if value is not None else "").replace(",", "").replace("NPR", "").strip()
    if not raw:
        if required:
            raise SourceError("REQUIRED_NUMBER_MISSING")
        return Decimal(0)
    if raw in BAD:
        raise SourceError("SOURCE_FORMULA_ERROR")
    try:
        result = Decimal(raw)
    except InvalidOperation:
        raise SourceError("INVALID_SOURCE_NUMBER") from None
    if not result.is_finite() or result < 0 or result.as_tuple().exponent < -2:
        raise SourceError("INVALID_SOURCE_PRECISION")
    return result

def scalar(value):
    return int(value) if value == value.to_integral_value() else float(value)

def total(rows, key):
    return sum((Decimal(str(row[key] or 0)) for row in rows), Decimal(0))

def select_unique_source(payload):
    files = payload.get("files", [])
    if payload.get("nextPageToken") or len(files) != 1:
        raise SourceError("KKG_LIVE_SOURCE_NONUNIQUE")
    item = files[0]
    identity = item.get("id", "")
    if (item.get("name") != LIVE_TITLE or
            item.get("mimeType") != "application/vnd.google-apps.spreadsheet" or
            item.get("trashed") is True or
            not re.fullmatch(r"[A-Za-z0-9_-]{20,}", identity)):
        raise SourceError("KKG_LIVE_SOURCE_MISMATCH")
    return identity

def derive(sheets, now=None):
    project = sheets["Bishal Paija"]
    master = sheets["Total"]
    memory = sheets["00_SYSTEM_MEMORY"]
    if not any(cell(r, 0) == "CURRENT_LIVE_VERSION" and cell(r, 1) == SOURCE_VERSION for r in memory):
        raise SourceError("KKG_SOURCE_VERSION_MISMATCH")
    if not project or project[0][:5] != ["Vendor ID", "Vendor / Purpose", "Amount (NPR)", "Discount (NPR)", "QR (NPR)"]:
        raise SourceError("KKG_PROJECT_SUMMARY_HEADER")
    vendors = []
    index = 1
    while index < len(project) and cell(project[index], 0) != "ALL VENDORS":
        r = project[index]
        if cell(r, 0) != str(len(vendors)+1) or not cell(r, 1):
            raise SourceError("KKG_VENDOR_SEQUENCE")
        vendors.append({"id": len(vendors)+1, "name":cell(r,1),
                        "amount_npr":scalar(decimal(cell(r,2),True)),
                        "discount_npr":scalar(decimal(cell(r,3))),
                        "qr_npr":scalar(decimal(cell(r,4))),
                        "payment_count":0})
        index += 1
    if index >= len(project) or len(vendors)<27 or len({v["name"] for v in vendors})!=len(vendors):
        raise SourceError("KKG_VENDOR_REGISTER_MISSING")
    declared = project[index]
    seen = set()
    payments = []
    sections = []
    cursor = index+1
    while cursor < len(project):
        match = HEADING.fullmatch(cell(project[cursor],0))
        if not match:
            if any(cell(project[cursor],col) for col in range(9)) and cell(project[cursor],0) != "":
                raise SourceError("KKG_UNEXPECTED_SECTION_CONTENT")
            cursor += 1
            continue
        vid = int(match.group(1))
        vendor = next((v for v in vendors if v["id"]==vid),None)
        if not vendor or match.group(2) != vendor["name"] or vid in sections:
            raise SourceError("KKG_VENDOR_BANNER")
        sections.append(vid)
        cursor += 1
        if (project[cursor][:6] !=
                ["Time","Date (BS / AD)","Amount (NPR)","Discount (NPR)","QR (NPR)","Entry ID"]):
            raise SourceError("KKG_MINI_TABLE_HEADER")
        cursor += 1
        entries = []
        while cursor < len(project) and cell(project[cursor],0) != "TOTAL":
            r=project[cursor]
            cursor+=1
            if not any(cell(r,k) for k in range(9)):
                continue
            stable_id,dt=cell(r,5),cell(r,1)
            if (not stable_id or stable_id in seen or not DATE.fullmatch(dt)
                    or not cell(r,2) or cell(r,7) not in
                    ("SOURCE_RECORDED_ONLY","REVIEW_REQUIRED","EVIDENCE_LINKED")):
                raise SourceError("KKG_PAYMENT_ID_DATE_STATUS")
            seen.add(stable_id)
            entry={"vendor_id":vid,"vendor":vendor["name"],"source_date":dt,
                   "date_system":"BS" if "_" in dt else "AD",
                   "paid_time":cell(r,0) or None,
                   "amount_npr":scalar(decimal(cell(r,2),True)),
                   "qr_npr":scalar(decimal(cell(r,4))),
                   "discount_npr":scalar(decimal(cell(r,3)))}
            entries.append(entry)
            payments.append(entry)
        if cursor >= len(project):
            raise SourceError("KKG_MINI_TABLE_MISSING_FOOTER")
        footer=project[cursor]
        for key,col in (("amount_npr",2),("discount_npr",3),("qr_npr",4)):
            calc=total(entries,key)
            if calc != Decimal(str(vendor[key])) or calc != decimal(cell(footer,col),True):
                raise SourceError("KKG_MINI_TABLE_ARITHMETIC")
        vendor["payment_count"]=len(entries)
        cursor+=1

    if sections != [v["id"] for v in vendors] or len(payments)<74 or len(seen)!=len(payments):
        raise SourceError("KKG_MINI_TABLE_COVERAGE")
    totals={"vendor_count":len(vendors),"payment_count":len(payments),
            "amount_npr":scalar(total(payments,"amount_npr")),
            "qr_npr":scalar(total(payments,"qr_npr")),
            "discount_npr":scalar(total(payments,"discount_npr"))}
    for key,col in (("amount_npr",2),("discount_npr",3),("qr_npr",4)):
        val=total(payments,key)
        if val!=decimal(cell(declared,col),True) or val!=total(vendors,key):
            raise SourceError("KKG_PROJECT_ROLLUP_DIFFERENCE")
    if not master or master[0][:4]!=["Project","Amount (NPR)","Discount (NPR)","QR (NPR)"]:
        raise SourceError("KKG_TOTAL_PROJECT_HEADER")
    if len(master)<3 or cell(master[1],0)!="Bishal Paija" or cell(master[2],0)!="TOTAL":
        raise SourceError("KKG_TOTAL_PROJECT_ROW")
    for key,col in (("amount_npr",1),("discount_npr",2),("qr_npr",3)):
        for row in master[1:3]:
            if decimal(cell(row,col),True)!=Decimal(str(totals[key])):
                raise SourceError("KKG_TOTAL_PROJECT_ROLLUP")
    if len(master)<5 or master[4][:4]!=["Vendor / Purpose","Amount (NPR)","Discount (NPR)","QR (NPR)"]:
        raise SourceError("KKG_TOTAL_VENDOR_HEADER")
    for i,vendor in enumerate(vendors):
        row=master[5+i]
        if cell(row,0)!=vendor["name"]:
            raise SourceError("KKG_TOTAL_VENDOR_ORDER")
        for key,col in (("amount_npr",1),("discount_npr",2),("qr_npr",3)):
            if decimal(cell(row,col),True)!=Decimal(str(vendor[key])):
                raise SourceError("KKG_TOTAL_VENDOR_VALUE")
    if len(master)<=5+len(vendors) or cell(master[5+len(vendors)],0)!="ALL VENDORS":
        raise SourceError("KKG_TOTAL_VENDOR_GRAND")
    ts=now or datetime.now(timezone.utc)
    return {"schema":"jp.finance.public.v1","version":"1.1.0",
            "verified_on":ts.date().isoformat(),"publication_mode":"github_actions_google_sheets",
            "source_synced_at_utc":ts.isoformat(timespec="seconds"),
            "company":"Rohini Engineering and Builders Pvt. Ltd.","company_id":"REB",
            "project":"14 Bishal Paija","project_id":"14_bishal_paija",
            "register":"Krishna Kumar Gupta — Payment to Project","currency":"NPR",
            "source":{"workbook_url":"source-sheets.html","register_tab":"Bishal Paija",
                      "vendor_range":"A1:E"+str(len(vendors)+2),
                      "payment_range":"A"+str(index+2)+":I"+str(cursor),
                      "mixed_date_systems":any(p["date_system"]=="BS" for p in payments)
                       and any(p["date_system"]=="AD" for p in payments)},
            "totals":totals,
            "checks":{"all_payment_ids_unique":True,"all_vendor_totals_match":True,
                      "source_grand_totals_match":True,"internal_ids_excluded_from_public_data":True},
            "vendors":vendors,"payments":payments}

def fetch_google():
    import google.auth
    from google.auth.transport.requests import AuthorizedSession
    credentials,_=google.auth.default(scopes=[
        "https://www.googleapis.com/auth/drive.metadata.readonly",
        "https://www.googleapis.com/auth/spreadsheets.readonly"])
    session=AuthorizedSession(credentials)
    safe=LIVE_TITLE.replace("\\","\\\\").replace("'","\\'")
    q=("name = '"+safe+"' and mimeType = "
       "'application/vnd.google-apps.spreadsheet' and trashed = false")
    resp=session.get("https://www.googleapis.com/drive/v3/files",
         params={"q":q,"pageSize":100,"fields":"nextPageToken,files(id,name,mimeType,trashed)"},
         timeout=30)
    if not resp.ok:
        raise SourceError("KKG_SOURCE_DISCOVERY_PERMISSION")
    identity=select_unique_source(resp.json())
    meta=session.get("https://sheets.googleapis.com/v4/spreadsheets/"+identity,
         params={"fields":"sheets(properties(title,gridProperties(rowCount)))"},timeout=30)
    if not meta.ok:
        raise SourceError("KKG_SOURCE_METADATA_PERMISSION")
    sh=meta.json().get("sheets",[])
    byname={s["properties"]["title"]:s["properties"]["gridProperties"]["rowCount"] for s in sh}
    if set(byname)!=set(TAB_NAMES):
        raise SourceError("KKG_THREE_TAB_CONTRACT")
    ranges=[f"'{name}'!A1:{'I' if name=='Bishal Paija' else 'D' if name=='Total' else 'C'}{rows}"
            for name,rows in ((name,byname[name]) for name in TAB_NAMES)]
    response=session.get("https://sheets.googleapis.com/v4/spreadsheets/"+identity+"/values:batchGet",
       params=[*(("ranges",x) for x in ranges),("valueRenderOption","FORMATTED_VALUE")],
       timeout=45)
    if not response.ok:
        raise SourceError("KKG_SHEETS_READ_PERMISSION")
    data=response.json().get("valueRanges",[])
    if len(data)!=3:
        raise SourceError("KKG_BATCH_SOURCE_INCOMPLETE")
    return {name:rows.get("values",[]) for name,rows in zip(TAB_NAMES,data)}

def self_test():
    fake={"Total":[["Project","Amount (NPR)","Discount (NPR)","QR (NPR)"],
                        ["Bishal Paija","100","4","10"],["TOTAL","100","4","10"],
                        [],["Vendor / Purpose","Amount (NPR)","Discount (NPR)","QR (NPR)"],
                        ["Hardware","100","4","10"],["ALL VENDORS","100","4","10"]],
          "Bishal Paija":[["Vendor ID","Vendor / Purpose","Amount (NPR)","Discount (NPR)","QR (NPR)"],
                          ["1","Hardware","100","4","10"],["ALL VENDORS","TOTAL","100","4","10"],[],
                          ["VENDOR 01 · Hardware"],["Time","Date (BS / AD)","Amount (NPR)","Discount (NPR)","QR (NPR)","Entry ID"],
                          ["2:00 pm","2083_01_17","100","4","10","KKG-01","","SOURCE_RECORDED_ONLY"],
                          ["TOTAL","","100","4","10"]],
          "00_SYSTEM_MEMORY":[["CURRENT_LIVE_VERSION",SOURCE_VERSION]]}
    # Minimal fixture tests parser's strongest validation gate before a live credential read.
    try:
        derive(fake)
    except SourceError as exc:
        assert str(exc)=="KKG_VENDOR_REGISTER_MISSING"
    else:
        raise AssertionError("Less than 27 original groups must not silently pass")
    a={"files":[{"id":"AbcDeFGhIjKlMnOpQrStUvWxYz1234",
                "name":LIVE_TITLE,"mimeType":"application/vnd.google-apps.spreadsheet"}]}
    assert select_unique_source(a)==a["files"][0]["id"]
    for wrong in ({}, {"files":a["files"]*2},
                  {"files":a["files"],"nextPageToken":"notdone"},
                  {"files":[dict(a["files"][0],name="Archived KKG")] }):
        try:
            select_unique_source(wrong)
        except SourceError:
            continue
        raise AssertionError("Nonunique or wrong Google source accepted")
    print("PASS KKG V1.1 live title discovery fail-closed; old archive cannot pass")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--output",type=Path,default=OUTPUT)
    args=parser.parse_args()
    try:
        if args.self_test:
            self_test()
        else:
            data=derive(fetch_google())
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print("PASS KKG authenticated V1.1 live read:",data["totals"]["vendor_count"],
                  "vendor groups,",data["totals"]["payment_count"],"source records; not certified.")
    except SourceError as exc:
        # Do not echo provider URL, source private ID or payment data in public Actions logs.
        print("FINANCE_REFRESH_FAILED: "+str(exc),file=sys.stderr)
        sys.exit(1)
