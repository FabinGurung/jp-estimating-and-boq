# A7/A9 Cost Estimation — existing source-to-publication tool arsenal

**Recorded:** 17 November 2026 (Asia/Kathmandu)  
**Repository:** `FabinGurung/jp-estimating-and-boq` · **research publishing branch:** `research/open-estimation-engine-v0.1`  
**Operating mode:** `MANUAL_FIRST_NO_CRON` — no scheduled interval and no auto-approved payments.

## What is already working

| Layer / resource | Current role | Authority / constraint |
| --- | --- | --- |
| Google Drive | Human original source and full native workbook PRE/POST + source-specific audit Docs | Every editable financial source retains its original Google Sheet ID. Old Excel, signed receipts, drawings and source invoices are preserved privately. |
| ChatGPT connected Google Drive/Sheets | When the account owner authorizes it, can read cells, inspect formulas, edit the SAME live ID, move/rename Drive files and create controlled A7 PRE/POST | Interactive user-scoped access is NOT GitHub Actions' identity. Never infer the GitHub runner can read a Sheet because the chat editor can. |
| Google Cloud `just-a-project-5007` | Existing keyless GitHub Workload Identity Federation, service account `jp-pages-publisher` | Short-lived authorized Google scopes; Viewer on each private original source Sheet. Vendor Bills and Contractor Bills Viewer grants are now configured. No new account/long-lived JSON key is required. |
| GitHub Estimation repository | Versioned import logic, audit and source-map schemas, CI and static site | Pull request + CI gate; PRE/POST Git snapshot branches used where appropriate. No raw private finance rows in public source. |
| Python source adapters | Read-only calls to private source and strict normalization/aggregate validation | See scripts below. No Google Sheets writes by the CI/deploy runner. |
| GitHub Actions | `.github/workflows/deploy-research-pages.yml`: separate Google auth, source imports, verification, Pages staging/deployment | Existing finance and Amrit paths are read on authorized publishing runs; Vendor/Contractor readers are explicitly selected by manual workflow dispatch or user-authorized marked push. |
| GitHub Pages | Static, versioned publication of validated public-safe reports | A deployment may show the last verified snapshot. Only an authenticated successful read in the staged artifact may say `MANUAL_AUTHENTICATED_READ`. Not a two-way live Google Sheets database. |
| A7 central Memory Wall | System-owner navigation and controlled release convention | Points at this Estimation source memory, not a second authoritative payments register. |
| Field & Desk Resource Library | Original project document/field evidence custody and links | Does not own independently editable vendor/contractor/payment calculation tables. |

### Exact source readers

- Krishna Kumar Gupta/Rohini `scripts/build_finance_from_google_sheets.py`: reads original `14_bishal_paija` and `KKG_VENDOR_SUMMARY_AUTO`; maintained source register `RE-KKG-FINANCE-LIVE`. Human template revision V000005 adds `Total`, `Bishal Paija` and `00_SYSTEM_MEMORY`, while the read adapter retains the original stable input tabs/ID.
- Fabin Gurung `scripts/build_fabin_finance_from_google_sheets.py`: reads the existing original Fabin finance data and publishes only source-scoped, non-certified project-level results. Basketball/Prithivi overlap remains isolated.
- Vendor Bills `scripts/build_vendor_bills_public.py`: reads `00_MANIFEST`, `VB_SOURCE_INDEX`, `VB_BILL_RECORDS`, `VB_DETAIL_ROWS`, `VB_RECONCILIATION`, `VB_REVIEW_QUEUE` through existing Google publishing identity and unique exact-title lookup (or optional private `JP_VENDOR_BILLS_SHEET_ID` override). Safe aggregate status: 35 source tabs, 1,895 source rows, 259 bills, 930 details, 46 comparisons and 509 OPEN reviews; no approved invoices inferred.
- Contractor Bills `scripts/build_contractor_bills_public.py`: reads original and normalized `CT_*` contractor claim tables under unique exact-title lookup or optional `JP_CONTRACTOR_BILLS_SHEET_ID` override. Previous authenticated manual source read succeeded on 17 Nov 2026, with 16 OPEN issues, no certified claims.
- Existing Amrit rates, measurement/BOQ and project finance paths continue under their distinct scripts and unchanged Google Sheet identities. The remaining two registered Sheets are reference/template books, NOT source importers.

The single public-safe machine source map is `data/connected-website-sheets.v1.json`, V000008 (eight working/reference workbook roles: four established authenticated readers, two optional manually triggered readers and two references/templates).

## Why separate Google Cloud permissions are required

The user/ChatGPT Google Drive connection and the GitHub-hosted workflow are different software principals. ChatGPT can use user-authorized connectors to inspect or edit private source data directly **during a conversation**. GitHub Actions runs later on a remote cloud worker, which cannot borrow the chat session's private OAuth token. It authenticates independently via keyless Workload Identity Federation and must be individually permitted to view the original Google Sheet.

The service account only needs **Viewer** on source files. The public website does not get a Google token or write access, and the workflow publishes only a validated safe aggregate. Exact-title source discovery is fail-closed on missing or multiple source files; a private secret containing a source ID remains optional. An authenticated source read does **not** mean the invoices, measurements or payments have passed commercial or tax approval.

## Manual publication procedure

1. Edit the source LIVE Google Sheet with A7 PRE → controlled evidence-backed edits → full source/normalized QA → POST in its original subject-specific history folder. Do NOT edit the POST copy as a second authority.
2. If the site needs a fresh Vendor or Contractor aggregate, go to [Deploy research website to GitHub Pages](https://github.com/FabinGurung/jp-estimating-and-boq/actions/workflows/deploy-research-pages.yml) on `research/open-estimation-engine-v0.1` and explicitly select the relevant required source read. The existing service account and Viewer permissions are reused.
3. The source adapter validates each public status: proper source tab list, unique record identifiers, totals/reconciliation and safe output-only schema. Missing source, ambiguous titles, failed permission or failed QA aborts rather than claiming live success.
4. Check the **specific** Actions job step and summary, and the deployed `sourceMode` field on Pages. `MANUAL_AUTHENTICATED_READ` means the aggregate was genuinely fetched and validated on that run. `VERIFIED_SNAPSHOT` means only an earlier checked fallback was published.
5. No cron/scheduled interval or automatic source writing/approval should be introduced until a future user-authorized template test and monitoring design.

## A7 and evidence boundaries

Google Drive is human source authority, GitHub stores repeatable logic and public-safe snapshots, Actions performs permissioned read/QA/deployment, Pages is the viewer and A7 is the cross-repository index. Vendor bills, contractor work claims and recorded project payment events are three different financial grains; don't add them blindly or infer cash settlement from a bill. The original company/project context remains distinct for Krishna and Fabin.

**Status is earned by the latest verified workflow result, not the existence of a configured workflow alone.** This is a design guardrail, not a promise of unattended refresh.
