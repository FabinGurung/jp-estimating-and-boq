/* Estimation-owned public-safe source map. Google Drive remains the editable authority.
 * Only user-invoked workflows and user-approved commits perform source reads.
 */
(() => {
  'use strict';
  const root=document.getElementById('estimationSourceCards');
  const count=document.getElementById('estimationSourceCount');
  if(!root)return;
  const make=(tag,cls,txt)=>{
    const x=document.createElement(tag);
    if(cls)x.className=cls;
    if(txt!==undefined)x.textContent=String(txt);
    return x;
  };
  fetch('data/connected-website-sheets.v1.json',{cache:'no-store'})
    .then(response=>{if(!response.ok)throw new Error('Source map unavailable');return response.json()})
    .then(data=>{
      if(data.schema!=='jp.website.connected-source-sheets.v1'||
         !Array.isArray(data.records)||data.records.length!==8||
         data.operatorPolicy?.mode!=='MANUAL_FIRST_NO_CRON')throw new Error('Source map contract mismatch');
      const feeds=data.records.filter(r=>r.fetchContract?.mode?.startsWith('AUTHENTICATED'));
      const optional=data.records.filter(r=>r.fetchContract?.mode?.startsWith('OPTIONAL_'));
      const references=data.records.filter(r=>r.fetchContract?.mode==='REFERENCE_ONLY'||r.fetchContract?.mode==='TEMPLATE_ONLY_NO_FETCH');
      if(feeds.length!==4||optional.length!==2||references.length!==2)throw new Error('Unexpected source role counts');
      count.textContent='4 established authenticated paths · 2 manually invoked Vendor/Contractor source readers · 2 reference/template Sheets · deployed source mode checked below · no scheduled interval · catalogue '+data.version;
      root.replaceChildren();
      for(const r of data.records){
        const fc=r.fetchContract;
        const optionalFeed=fc.mode.startsWith('OPTIONAL_');
        const active=fc.mode.startsWith('AUTHENTICATED')||optionalFeed;
        const card=make('article','jp-source-item '+(optionalFeed?'is-optional':active?'is-active':'is-reference'));
        const top=make('div','jp-source-item-head');
        const tag=make('span','jp-source-item-tag',optionalFeed?'OPTIONAL MANUAL READ':active?'AUTHENTICATED SOURCE PATH':'REFERENCE / TEMPLATE');
        const ref=make('code','jp-source-item-ref',r.ref);
        top.append(tag,ref);
        const title=make('h3','',r.title);
        const role=make('p','jp-source-item-role',r.authority);
        const output=make('p','jp-source-item-output','Output: '+fc.output);
        const source=make('p','jp-source-item-outcome','Status: '+r.publicationStatus);
        card.append(top,title,role,output,source);
        // The repository JSON is a verified fallback. Only the DEPLOYED status
        // from the last authenticated run can certify a manual live source read.
        if(optionalFeed && (r.ref==='JP-VENDOR-BILLS-LIVE'||r.ref==='JP-CONTRACTOR-BILLS-LIVE')){
          fetch(fc.output,{cache:'no-store'})
            .then(response=>{if(!response.ok)throw new Error('Current status unavailable');return response.json()})
            .then(payload=>{
              const mode=payload.sourceMode;
              if(!/^V[0-9]{6}$/.test(payload.revision)||!['VERIFIED_SNAPSHOT','MANUAL_AUTHENTICATED_READ'].includes(mode))
                throw new Error('Bad public source status');
              const label=mode==='MANUAL_AUTHENTICATED_READ'?'Last deployed: authenticated manual Google source read':'Last deployed: verified aggregate snapshot';
              source.textContent=label+' · '+payload.revision+' · refresh manually when required';
              tag.textContent=mode==='MANUAL_AUTHENTICATED_READ'?'MANUAL READ VERIFIED':'MANUAL SOURCE · SNAPSHOT';
            })
            .catch(()=>{source.textContent='Public status temporarily unavailable; consult the latest Actions run';});
        }
        if(active){
          const detail=make('details','jp-source-item-detail');
          const summary=make('summary','',fc.readTabs.length+(optionalFeed?' configured read-only tabs · explicitly triggered · ':' exact tabs read · ')+fc.importer);
          const ul=make('ul','jp-source-tabs');
          for(const name of fc.readTabs)ul.append(make('li','',name));
          detail.append(summary,ul);
          card.append(detail);
        }else{
          card.append(make('p','jp-source-item-detail-text','This workbook is a reference/template. No live Google Sheets importer is configured.'));
        }
        const lower=make('p','jp-source-item-caution','Approval: '+fc.approval);
        const link=make('a','jp-source-item-open','Open related Estimation page');
        link.href=r.usagePage;
        card.append(lower,link);
        root.append(card);
      }
    }).catch(()=>{
      if(count)count.textContent='Source catalogue is unavailable; follow the existing directory.';
      const fallback=make('p','jp-source-error','Could not load current source details. The working source directory remains available.');
      root.replaceChildren(fallback);
    });
})();