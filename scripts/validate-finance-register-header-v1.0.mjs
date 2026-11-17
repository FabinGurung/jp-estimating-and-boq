import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read = path => readFileSync(new URL('../'+path, import.meta.url), 'utf8');
const html = read('finance.html');
const js = read('finance-register-header-v1.0.js');
const css = read('finance-register-header-v1.0.css');
const panel = read('finance-source-panels-v0.9.js');
const manifest = JSON.parse(read('site-page-registry.v0.8.json'));
const snapshot = JSON.parse(read('finance-public-snapshot.json'));
const metadata = JSON.parse(read('finance-sheet-meta-v1.1.json'));
const start = html.indexOf('<header class="topbar jp-fn-s01-topbar">');
const end = html.indexOf('</header>',start);
assert(start >= 0 && end > start,'Finance header not found');
const header = html.slice(start,end);
for(const required of ['fnS01Native','fnS01TablePanel','fnS01Search','fnS01Vendor','fnS01Calendar',
    'fnS01Limit','fnS01Previous','fnS01Next','fnS01TabIdentity','fnS01CopyTabId','fnS01ActiveSheetId']){
    assert(header.includes(required),'Missing native Finance UI control '+required);
}
assert(header.includes('<details open>')&&!header.includes('<iframe'));
assert((header.match(/role="tab"/g)||[]).length===3,'Exactly 3 current public-safe source tabs');
assert.equal(metadata.schema,'jp.finance.source-tab-metadata.v1');
assert.equal(metadata.sourceCode,'FN-S01');
assert.equal(metadata.sourceTitle,'Krishna Kumar Gupta — Payments to Projects — LIVE — V1.1');
assert.equal(metadata.inventoryStatus,'CURRENT_CANONICAL_THREE_TAB_PUBLIC_SAFE_SUBSET');
assert.equal(metadata.spreadsheetId,'PRIVATE_IN_GOOGLE_DRIVE');
assert.equal(metadata.sourceTabCount,3);
assert.equal(metadata.visibleTabCount,3);
assert.equal(metadata.excludedHiddenTabCount,0);
assert.equal(metadata.lastObservedLiveTabCount,3);
const expected=[['vendors','Total',1177922624],['payments','Bishal Paija',846338599],
                ['guide','00_SYSTEM_MEMORY',256073749]];
assert.deepEqual(metadata.tabs.map(t=>[t.viewId,t.title,t.sheetId]),expected);
for(const [view,title,gid] of expected){
  assert(header.includes('data-fn-s01-tab="'+view+'"'));
  assert(header.includes('>'+title+'</button>'));
  assert(js.includes("id: '"+view+"', title: '"+title+"', sheetId: "+gid));
}
assert(js.includes("fetch('finance-public-snapshot.json'"));
assert(js.includes("navigator.clipboard.writeText(String(view.sheetId))"));
assert(js.includes("source_date")&&js.includes("paid_time"));
assert(js.includes("aria-selected")&&js.includes("ArrowRight"));
assert(js.includes("replaceChildren(table)")&&js.includes("textContent"));
assert(!js.includes('<iframe')&&!js.includes('/preview'));
assert(panel.includes("if(source.id==='FN-S01')")&&panel.includes("native.scrollIntoView"));
assert(!header.includes('data-finance-source="FN-S01"'));
assert(header.includes('Read-only')||header.includes('read-only'));
assert(css.includes('overflow-x:auto')&&css.includes('@media(max-width:760px)'));
for(const file of [html,js,JSON.stringify(metadata),JSON.stringify(snapshot)]){
  assert(!file.includes('1S1fkWzo6XGzyD3p92_pTG32zZ9fF3YICAv3HPTomZsE'),
     'Retired private Sheet ID must not be exposed on public Finance pages');
  assert(!file.includes('1-DhklD5WyvNtsYNpEgvisIOlzNA6iSX_U3Bqci4FZ7I'),
     'New private LIVE ID must not be exposed');
}
assert.equal(snapshot.source.workbook_url,'source-sheets.html');
assert.equal(snapshot.totals.vendor_count,snapshot.vendors.length);
assert.equal(snapshot.totals.payment_count,snapshot.payments.length);
for(const key of ['amount_npr','qr_npr','discount_npr']){
  assert.equal(snapshot.payments.reduce((v,x)=>v+(x[key]||0),0),snapshot.totals[key]);
  assert.equal(snapshot.vendors.reduce((v,x)=>v+(x[key]||0),0),snapshot.totals[key]);
}
for(const row of snapshot.payments){
  assert(['BS','AD'].includes(row.date_system));
  for(const secret of ['entry_id','created_at','updated_at'])assert(!Object.hasOwn(row,secret));
}
const finance = manifest.pages.find(p=>p.id==='FN-01');
assert(finance?.sections?.some(s=>s.id==='FN-01.S06'&&s.domId==='fnS01Native'));
assert(finance?.keyDependencies?.includes('finance-register-header-v1.0.js'));
console.log('FN-S01 V1.1 PASS: 3 current private native tabs represented as public-safe views, stable payment projection verified, zero private file IDs.');
