(() => {
  'use strict';
  const root=document.getElementById('wageSummaries');
  if(!root)return;
  const make=(tag,p,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;p.append(e);return e;};
  const fmt=new Intl.NumberFormat('en-IN',{maximumFractionDigits:2});
  const number=v=>typeof v==='number'&&Number.isFinite(v)?fmt.format(v):v===''?'—':String(v??'—');
  function table(parent,headers,rows){
    const table=make('table',make('div',parent,undefined,'table-scroll'),undefined,'register-table');
    const tr=make('tr',make('thead',table));for(const h of headers)make('th',tr,h);
    const body=make('tbody',table);for(const r of rows){const row=make('tr',body);for(const v of r)make('td',row,number(v));}
  }
  Promise.all(['data/clean-wage-summaries.json','data/registers-links.json'].map(u=>fetch(u,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json()}))).then(([data,links])=>{
    if(data.schema!=='jp.clean-wage-summaries.v1'||!Array.isArray(data.sections))throw Error();
    const urls=new Map(links.groups.flatMap(g=>g.cards.map(c=>[c.key,c.url])));
    root.replaceChildren();
    make('p',root,'Source read: '+new Date(data.readAtUtc).toLocaleString('en-GB',{timeZone:'Asia/Kathmandu'})+' NPT','caption');
    for(const s of data.sections){
      const details=make('details',root,undefined,'source-group');make('summary',details,s.title+' — CLEAN');
      const a=make('a',details,'Open original Summary worksheet');a.href=urls.get(s.key);a.target='_blank';a.rel='noopener noreferrer';
      make('p',details,'Source: '+s.range+' · no new calculations','caption');
      table(details,['Recorded measure','Source total'],Object.entries(s.totals));
      if(s.sites.length){const sub=make('details',details,undefined,'source-group');make('summary',sub,'By project site ('+s.sites.length+')');table(sub,s.siteHeaders,s.sites);}
      if(s.workers.length){const sub=make('details',details,undefined,'source-group');make('summary',sub,'By worker code ('+s.workers.length+')');table(sub,s.workerHeaders,s.workers);}
    }
  }).catch(()=>{root.textContent='Summary unavailable. Open the original CLEAN workbooks above.';});
})();