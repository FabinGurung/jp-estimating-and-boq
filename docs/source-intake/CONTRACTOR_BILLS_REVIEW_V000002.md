# Contractor Bills — V000002 controlled normalization and manual publication

**Date:** 16 November 2026 (Asia/Kathmandu)  
**Owner:** `FabinGurung/jp-estimating-and-boq`  
**Live Sheet:** `03 — Bill of Contractors — Working Register — LIVE` in the existing restricted `Cost Estimation — Working Google Sheets` folder. Its permanent Sheet ID remains private in Drive (not published on Pages).  
**Control revision:** V000002. **Normalized-data revision:** V000001. **Approval status:** no certified contractor claims or confirmed payments.

## Source accounting and work grain

The workbook preserves six original tabs, including two historical Bishal Paija lists, `Hari_Chaudhari`, `Khem_Bahadur_Thapa`, and two empty historical tabs, alongside two original control tabs. Ten added `CT_*` views present the 2 source claim summaries, 33 primary work items, 34 historical **non-additive** rows, 5 source reconciliations, 16 OPEN review issues and 80 source-indexed populated original rows. All original source cells, formula references, Discord links and sheet IDs are preserved. Both empty tabs and historical alternate tabs remain in the file, hidden but indexed; no data deletion or payment approval was performed.

Source-reported Hari work amount is **NPR 2,65,521.462** across 33 lines and matches the source claim and original formula. Khem's source claim is zero and has no populated work items; the original source formula references the Rate column and remains flagged for later controlled review. The first 20 lines of an alternative Bishal list exactly match the first 20 main work records; a seven-line historical subtable repeats earlier work; seven older Discord-linked entries include a composite grouping. None of these historic views must be added to the primary claim. All five comparison differences are zero. Currency, project/party identity, dates, unit rates, quantities, certificates and payment evidence remain **unverified**.

## A7/Drive controls

A complete V000002 PRE copy was created before any edit, a complete V000002 POST copy after readback, both stored in the dedicated restricted Contractor Bills version-history folder. The original native Sheet ID was retained and the live workbook moved/renamed in place. A new restricted Contractor Bills audit Google Doc beside the live working Sheet holds original source details, lineage, all controls and exact PRE/POST recovery links. The original Excel workbook was left untouched. Do not maintain a second editable working copy.

## GitHub / Pages source boundary

This Estimation repository owns a machine source-map record (`JP-CONTRACTOR-BILLS-LIVE`), aggregate-only checked snapshot (`data/contractor-bills-status.v1.json`), read-only Google Sheets adapter (`scripts/build_contractor_bills_public.py`) and Memory Wall panel. Publication is **VERIFIED_SNAPSHOT V000002**, **not** a confirmed authenticated Google Sheet read. The existing Google publishing service account has now been granted Viewer on the original LIVE Sheet. An explicit `workflow_dispatch` with `require_contractor_live=true` or an authorized research publishing push tagged `[contractor-manual-read]` requests authenticated refresh. The importer resolves the unique, exact-titled shared Sheet by read-only Drive metadata; the private repository secret `JP_CONTRACTOR_BILLS_SHEET_ID` is an optional override, not a prerequisite. A successful validated live fetch switches the staged public aggregate to `MANUAL_AUTHENTICATED_READ`; an ordinary commit deployment does not.

Public pages show only aggregate record counts, versions and unresolved statuses. No live Sheet IDs, private supplier/contractor identifiers, invoices, source amounts, Discord URLs, payment rows or credentials are committed to public Pages. Finance and project measurements belong to Estimation; scanned originals and site evidence custody remain with the Field & Desk Resource Library. No Resources repository files were changed. No cron or unattended interval was added.

## Next controlled manual evidence work

1. Obtain signed RA/measurement certification and contract identity before approving any claim.
2. Verify contractor project crosswalk and distinguish construction work dates from bank/receipt payment dates.
3. Confirm Khem Rate-vs-Amount source formula semantics in a new A7 PRE → same LIVE Sheet ID edit → POST.
4. Preserve the historical alternate and Discord-linked rows as evidence without double counting.
5. Before claiming a live authenticated fetch, verify the GitHub Actions run summary and source read permission. Existing snapshot is a validated prior state, not live freshness.
