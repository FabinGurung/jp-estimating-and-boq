/* Controlled source roles are public. No credentials, Google tokens or private rows here. */
(()=>{'use strict';
const container=document.getElementById('sheetInventoryRows');
if(!container)return;
fetch('data/connected-website-sheets.v1.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Missing inventory');return r.json();}).then(d=>{
if(d.schema!=='jp.website.connected-source-sheets.v1'||!Array.isArray(d.records))throw Error('Schema mismatch');
container.replaceChildren();
for(const r of d.records){
const card=document.createElement('article');card.className='tile';
const heading=document.createElement('h3');heading.textContent=r.title;
const type=document.createElement('p');const b=document.createElement('strong');b.textContent='Source role: ';type.append(b,document.createTextNode(r.authority));
const status=document.createElement('p');const s=document.createElement('strong');s.textContent='Publication status: ';status.append(s,document.createTextNode(r.publicationStatus.replaceAll('_',' ')));
const link=document.createElement('a');link.href=r.usagePage;link.textContent='Open relevant website view →';
const warning=document.createElement('p');warning.className='muted';warning.textContent='Does not imply: '+r.doesNotImply;
card.append(heading,type,status,warning,link);container.append(card);
}
}).catch(()=>{container.textContent='Source-role inventory unavailable. Open the original Drive folder above to find the controlled LIVE Sheets.'});
})();

(() => {
  'use strict';
  const status = document.getElementById('sourceSyncStatus');
  if (!status) return;
  const json = async (path) => {
    const response = await fetch(path, {cache: 'no-store'});
    if (!response.ok) throw Error('No published receipt');
    return response.json();
  };
  const make = (parent, tag, text) => {
    const element = document.createElement(tag);
    element.textContent = text;
    parent.append(element);
    return element;
  };
  const count = value => new Intl.NumberFormat('en-IN').format(value);
  const feeds = [
    ['KKG payment reconciliation', 'data/kkg-finance-source-status.json', d => d.reconciled === true],
    ['Fabin payment aggregates', 'fabin-payments-public.json', d => d.authenticatedSourceFetch === true],
    ['Vendor bill status', 'data/vendor-bills-status.v2.json', d => d.sourceMode === 'MANUAL_AUTHENTICATED_READ'],
    ['Contractor bill status', 'data/contractor-bills-status.v1.json', d => d.sourceMode === 'MANUAL_AUTHENTICATED_READ'],
    ['Income reconciliation', 'data/income-register-status.v1.json', d => d.sourceMode === 'MANUAL_AUTHENTICATED_READ']
  ];
  const finance = document.getElementById('sourceSyncFinance');
  Promise.all(feeds.map(async ([label, path, isCurrent]) => {
    try {
      return [label, isCurrent(await json(path))];
    } catch {
      return [label, false];
    }
  })).then(results => {
    for (const [label, verified] of results) {
      make(finance, 'li', label + (verified ? ' · Authenticated source read published' : ' · Historical view or read pending'));
    }
  });
  json('data/estimating-source-receipt.json').then(receipt => {
    if (receipt.schema !== 'jp.estimating.source-receipt.v1') throw Error('Unexpected receipt');
    const date = new Intl.DateTimeFormat('en-IN', {dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Kathmandu'});
    status.textContent = 'Last verified Google Drive read ' + date.format(new Date(receipt.readAtUtc)) + ' NPT';
    const list = document.getElementById('sourceSyncResults');
    make(list, 'li', count(receipt.counts.pdfRateObservations) + ' PDF observations and numeric candidates across six sources');
    make(list, 'li', count(receipt.counts.indicativeRates) + ' indicative rate rows');
    make(list, 'li', count(receipt.counts.restrictedFieldSources) + ' private field sources indexed');
    const items = document.getElementById('sourceSyncBbs');
    for (const entry of receipt.reinforcement) {
      make(items, 'li', entry.item + (entry.sourceRead ? ' · Source read verified' : ' · Source read pending'));
    }
    const guide = document.getElementById('sourceSyncGuide');
    for (const paragraph of receipt.guidance) make(guide, 'p', paragraph);
    return json('data/estimating-indicative-rates.json');
  }).then(rates => {
    const rows = document.getElementById('liveRateRows');
    for (const item of rates) {
      const row = make(rows, 'tr', '');
      for (const value of [item.item, item.basis, count(item.lowNpr), count(item.highNpr), item.unit]) {
        make(row, 'td', value);
      }
    }
  }).catch(() => {
    status.textContent = 'A verified Google Drive source receipt is unavailable on this deployment.';
  });
})();
