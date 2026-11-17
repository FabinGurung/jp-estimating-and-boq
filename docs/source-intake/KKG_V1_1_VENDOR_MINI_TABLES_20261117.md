# KKG / Rohini — V1.1 human vendor mini-tables and authenticated source contract

**Recorded:** 17 November 2026 · **Owner:** A9 Cost Estimation · **A7 control:** V000002 · **Current status:** new LIVE source workbook migration QA passed; Pages source read requires independent Actions verification.

## Authority / source migration

The original Krishna Kumar Gupta Payments to Projects 20-tab V0.5 Google Sheet was preserved in its **restricted A7 Version History folder**, with a complete **V000007 PRE** and the original file retained as a retired source. A separate human-made copy was numbered **V000006 MANUAL_COPY** (not a PRE). A completely new native Google Sheet V1.0 was created with three tabs only and became the single LIVE editable KKG source. This newer V1 workbook retains the **same new permanent ID** through its V1.1 mini-table restructure. A full V000002 PRE was created before editing V1.0; a full V000002 POST was copied after source reconciliation.

**No private Sheet IDs, invoice attachments, account identifiers or PRE/POST URLs belong in this public repository.** The restricted KKG A7 audit Google Doc alongside the live working file stores exact identifiers, rollback instructions, original Excel lineage and row-level reconciliation.

## LIVE V1.1 worksheet contract

| Worksheet | Operator role | Visible content |
|---|---|---|
| `Total` | Read-only-by-convention master display | Project summary + 27 vendor totals, hyperlinked to vendor section footers; no instructions or migrated raw registers |
| `Bishal Paija` | **Only operator-editable source payment sheet** | `A1:E29`: 27 vendor names and formula-linked Amount, Discount, QR; `A32:I293`: 27 separate vendor mini-tables, each with 3 spare blank rows and a formula footer |
| `00_SYSTEM_MEMORY` | Private A7 change journal and governance | Original 20-tab inventory and old memory/audit records; V1/1.1 migration history, PRE/POST, future source editing rules, dates, certification status, publishing contract |

Vendor entry columns in each mini-table: **Time | Date (BS or AD) | Amount (NPR) | Discount (NPR) | QR (NPR) | Entry ID | Legacy row | Review status | Evidence / Notes**. The first five are the human-first payment fields. Entry IDs and original row references remain available inside the restricted Google Sheet. Source dates/times and discounts/QR must not be inferred or converted.

Each vendor's mini-table footer uses live `SUM` of that section's Amount, Discount and QR. The top project summary contains links to those footer amounts; `Total` reads the project/vendor rollups. Operators edit ONLY the actual vendor mini-table entries. The top summary and Total are derived; do not enter amounts into them. Three blank mini-table rows are reserved per vendor; for additional records, insert above the vendor footer and ensure formula ranges and unique Entry IDs remain valid. Adding an entirely new vendor requires an A7-controlled new summary row + new mini-table + checked links.

## Reconciliation

Compared the V1.0 complete V000002 PRE against the same-ID V1.1 live file before creating POST. **74/74 stable Entry IDs, 27/27 vendor identities** and every payment's recorded date, time, amount, discount, QR, legacy row, review status and notes reconciled without a field difference. Amount **NPR 268,798**, Discount **NPR 2,400** and QR **NPR 160** separately reconcile in vendor footers, both summaries and the master project total. Values remain **SOURCE_RECORDED_NOT_CERTIFIED**, never automatic bank/tax/project-payment approval.

## GitHub Actions, Pages and A7

The source registry role remains `RE-KKG-FINANCE-LIVE`, but its display version is **V1.1 / V000002**, not the retired V0.5. The new read-only Python importer `scripts/build_finance_from_google_sheets.py` discovers the **unique exact LIVE title** through the existing Google Workload Identity/Drive metadata access. It validates exactly three tabs, the current Memory control, 27+ vendor sections, unique payment IDs, mini-table footers, project summary, and Total before producing the existing public finance JSON shape. It must not read the archived workbook merely because an ID still exists.

Public navigation points to the governed source directory, not a private source URL. Old historical snapshots remain date-labeled; an updated GitHub commit or local Sheet QA is **not equivalent to an authenticated Pages read**. The publishing workflow runs manually/explicitly—**no cron**, no background payment writes. Existing independent Fabin and Vendor Bills schema issues remain separate (issues #62 and #64); a KKG-only authorized marked release may explicitly skip the unrelated broken Fabin adapter with a warning while leaving its data untouched. Preserve A7 Git PRE/PR/CI/POST.

Historic predecessor for lineage: `KKG_V000005_FABIN_TEMPLATE_ALIGNMENT.md`. Current governance is this document and the restricted `00_SYSTEM_MEMORY` plus QA Google Doc.
