# Krishna Kumar Gupta — V000005 human presentation and `00_SYSTEM_MEMORY`

**Source:** The existing permanent native Google Sheet titled `Krishna Kumar Gupta — Payments to Projects — Working v0.5`, in the existing restricted Cost Estimation working Google Sheets folder.  
**Company/project:** Rohini Engineering and Builders Pvt. Ltd. — 14 Bishal Paija.  
**Version control:** Full native V000005 PRE and POST archived in the existing KKG history folder; same original live ID retained. A private QA Google Doc beside the live Sheet contains exact file links and source/cell-level evidence.

## Reference followed

The user expressly supplied Fabin Gurung Payments to Projects `00_SYSTEM_MEMORY` (gid 1001) as the reference architecture. The relevant rules are: one LIVE source of truth, human-readable `Total` and project tabs, per-vendor five-column mini-tables `Time | Date | Amount | Discount | QR`, five-column project summary `ID | Name | Amount | Discount | QR`, `SUBTOTAL(109,...)` rollups, two-way ▲ back links, BS dates `YYYY_MM_DD`, AD dates `YYYY-MM-DD` or `YYYY/MM/DD`, NPR 2-decimal figures, stable source IDs, audit and no financial approval from arithmetic matching.

Fabin's raw project entries and Basketball/Prithivi overlap policy were NOT copied into Krishna's separate Rohini payment source.

## Exact LIVE change

- **Added** `Total`: single-project master summary, source-vs-linked arithmetic check, and links to source and normalized views.
- **Added** `Bishal Paija`: 27 native-source-linked vendor top-summary entries with amount/discount/QR kept separate, then 27 linked five-column display mini-tables covering all original 74 individual entries. Each section has `SUBTOTAL(109,...)` and return links.
- **Added** `00_SYSTEM_MEMORY`: company-specific original source authority, related entity/table grain, date and money rules, manual source-entry guide, version history, unresolved holds and publishing source/identity map.
- **Updated only controls** in `00_START_HERE`, `00_SITE_CONTEXT`, `00_MANIFEST`, `00_PAYMENT_SUMMARY`, `01_VERSION_HISTORY` and the Drive display title to V000005.
- **Reordered** tabs to show `Total`, `Bishal Paija`, original `14_bishal_paija` first, followed by the original normalized and audit views; five previously hidden source/archive tabs stay hidden.
- **Retained** the exact original `14_bishal_paija` native tables, `KKG_VENDOR_SUMMARY_AUTO`, 27 vendor rows, 74 source Event IDs, original source dates/times, QR, discounts and formulas. No original finance source cells were edited.

## Independent QA

Complete PRE versus LIVE source value comparisons passed for original `14_bishal_paija!A1:H195`, `KKG_VENDOR_SUMMARY_AUTO!A1:E31`, `01_VENDOR_REGISTER!A1:J28` and `02_PAYMENT_EVENTS!A1:K75`. All 16 original sheet IDs and names are preserved; live workbook now has 19 tabs. All 27 new mini-tables have line counts and arithmetic equal to their original vendor sources. All 74 payment rows appear exactly once in the new linked presentation. Amount is NPR 2,68,798.00, QR NPR 160.00 and discount NPR 2,400.00; each separately reconciles. No displayed formula errors appeared in the scanned original source. No bank receipts or approvals were independently verified.

## Critical ongoing limits

The original `14_bishal_paija` is still the **only editable source**. The new `Bishal Paija` is linked for the current 27 vendor/74 source-entry shape, not a self-extending add-vendor program. The native "Add Vendor" Apps Script is still **prepared but not installed**. Future source entries or vendors require a new A7 PRE → same live ID edit → regeneration of derived views → source/ID/reconciliation QA → POST.

The existing GitHub KKG finance importer still reads the original `14_bishal_paija` and `KKG_VENDOR_SUMMARY_AUTO`, so the added display/memory tabs do not change the authenticated reader contract.

**Status:** source-recorded only, not bank-, contract- or tax-certified.
