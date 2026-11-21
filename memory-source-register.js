/* Cost Estimation source roles are public, underlying Sheet identities and finance rows remain private. */
(()=>{
 'use strict';
 const root=document.getElementById('estimationSourceCards');
 const count=document.getElementById('estimationSourceCount');
 if(!root)return;
 const make=(tag,cls,txt)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(txt!==undefined)e.textContent=String(txt);return e};
 async function readJson(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error('Missing artifact');return r.json()}
 async function loadStatus(r){
  const fc=r.fetchContract;
  const urls=r.ref==='JP-VENDOR-BILLS-LIVE'?[fc.output,'data/vendor-bills-status.v1.json']:[fc.output];
  for(const url of urls){
   try{const p=await readJson(url);
    if(!['MANUAL_AUTHENTICATED_READ','VERIFIED_SNAPSHOT'].includes(p.sourceMode))continue;
    const version=p.revision||p.sourceVersion;
    if(!/^V[0-9]{6}$/.test(version))continue;
    if(r.ref==='JP-VENDOR-BILLS-LIVE' && p.schema==='jp.vendor-bills-status.v2' && (p.privacy?.transactionRowsPublished!==0 || p.reviewFlags!==null))continue;
    if(r.ref==='JP-FABIN-INCOME-LIVE' && (p.schema!=='jp.fabin-income.status.v1'||p.privacy?.publishedIncomeAmounts!==0))continue;
    return {p,version};
   }catch(_){}
  }
  throw Error('No confirmed artifact');
 }
 readJson('data/connected-website-sheets.v1.json').then(data=>{
  if(data.schema!=='jp.website.connected-source-sheets.v1'||!Array.isArray(data.records)||data.records.length!==6||
    data.operatorPolicy?.mode!=='MANUAL_FIRST_NO_CRON')throw Error('Unexpected catalogue');
  const feeds=data.records.filter(r=>r.fetchContract?.mode?.startsWith('AUTHENTICATED'));
  const optional=data.records.filter(r=>r.fetchContract?.mode?.startsWith('OPTIONAL_'));
  const references=data.records.filter(r=>r.fetchContract?.mode==='REFERENCE_ONLY');
  if(feeds.length!==2||optional.length!==3||references.length!==1)throw Error('Wrong source categories');
  if(count)count.textContent='5 finance working registers + 1 permanent rate master · 2 build-time readers · 3 optional manual readers · public-safe output only · no cron · catalogue '+data.version;
  root.replaceChildren();
  for(const r of data.records){
   const fc=r.fetchContract;
   const isOptional=fc.mode.startsWith('OPTIONAL_');
   const isActive=fc.mode.startsWith('AUTHENTICATED')||isOptional;
   const card=make('article','jp-source-item '+(isOptional?'is-optional':isActive?'is-active':'is-reference'));
   const top=make('div','jp-source-item-head');
   const tag=make('span','jp-source-item-tag',isOptional?'MANUAL SOURCE READER':isActive?'AUTHENTICATED SOURCE PATH':'PERMANENT RATE REFERENCE');
   const ref=make('code','jp-source-item-ref',r.ref);top.append(tag,ref);
   const title=make('h3','',r.title);
   const role=make('p','jp-source-item-role',r.authority);
   const output=make('p','jp-source-item-output','Output: '+(fc.output||'Source library / no live export'));
   const source=make('p','jp-source-item-outcome','Status: '+r.publicationStatus);
   card.append(top,title,role,output,source);
   if(isOptional){
    loadStatus(r).then(({p,version})=>{
     const mode=p.sourceMode==='MANUAL_AUTHENTICATED_READ'?'Last staged/deployed artifact: authenticated Google read':'Historical verified snapshot; NOT current live source read';
     source.textContent=mode+' · '+version+' · manually refresh when needed';
     tag.textContent=p.sourceMode==='MANUAL_AUTHENTICATED_READ'?'MANUAL READ VERIFIED':'HISTORICAL SNAPSHOT ONLY';
    }).catch(()=>{source.textContent='No verified public source artifact available yet; private Google Sheet remains authoritative.'});
   }
   if(isActive){
    const d=make('details','jp-source-item-detail');
    const summary=make('summary','',fc.readTabs.length+' configured read-only tabs · '+fc.importer);
    const ul=make('ul','jp-source-tabs');
    for(const tab of fc.readTabs)ul.append(make('li','',tab));
    d.append(summary,ul);card.append(d);
   }else card.append(make('p','jp-source-item-detail-text','Human-maintained permanent source reference; no current approved-rate Actions importer.'));
   card.append(make('p','jp-source-item-caution','Approval: '+fc.approval));
   const link=make('a','jp-source-item-open','Open related Estimation page');link.href=r.usagePage;
   card.append(link);root.append(card);
  }
 }).catch(_=>{
  if(count)count.textContent='Source catalogue unavailable; please use the governed Drive folder.';
  root.replaceChildren(make('p','jp-source-error','Current source role registry unavailable.'));
 });
})();
