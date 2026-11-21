/* Vendor Bills: prefer the current authenticated V2 six-section status when present;
 * historical V000004 V1 snapshots remain a clearly dated fallback, never current QA.
 */
(() => {
  'use strict';
  const root=document.getElementById('vendor-bills-status');
  if(!root)return;
  const status=root.querySelector('[data-vendor-status]');
  const list=root.querySelector('dl');
  const fmt=new Intl.NumberFormat('en-IN');
  const finite=n=>Number.isSafeInteger(n)&&n>=0;
  const oldFields=[
    ['sourceTabs','Original source tabs'],
    ['sourceRows','Historical indexed rows'],
    ['billRows','Bill records'],
    ['detailRows','Detail rows'],
    ['comparisonRows','Comparisons'],
    ['reviewFlags','Historical review flags']
  ];
  const liveFields=[
    ['originalSourceTabsDeclared','Original tabs (manifest)'],
    ['machineRows','Current machine section records'],
    ['billRows','Bills'],
    ['summaryRows','Summaries'],
    ['comparisonRows','Reconciliations'],
    ['projectCrosswalkRows','Project crosswalk'],
    ['vendorCrosswalkRows','Vendor crosswalk'],
    ['detailRows','Detail lines'],
    ['reviewFlags','Current review flags']
  ];
  async function fetchJson(url){
    const response=await fetch(url,{cache:'no-store'});
    if(!response.ok)throw Error('No status');
    return response.json();
  }
  function show(data,isLive){
    const fields=isLive?liveFields:oldFields;
    if((isLive?data.schema!=='jp.vendor-bills-status.v2':data.schema!=='jp.vendor-bills-status.v1')||
      !/^V[0-9]{6}$/.test(data.revision)||
      fields.some(([k])=>!(isLive&&k==='reviewFlags'&&data[k]===null)&&!finite(data[k])))throw Error('Invalid status');
    if(isLive && (data.sourceMode!=='MANUAL_AUTHENTICATED_READ'||
                  data.financialApproval!=='NOT_VERIFIED'||
                  data.privacy?.transactionRowsPublished!==0||
                  data.privacy?.projectAmountsPublished!==0))throw Error('Unsafe V2 public status');
    list.replaceChildren();
    for(const [key,label] of fields){
      const group=document.createElement('div');
      const dt=document.createElement('dt');
      const dd=document.createElement('dd');
      dt.textContent=label;
      dd.textContent=data[key]===null?'Not established in current registry':fmt.format(data[key]);
      group.append(dt,dd);list.append(group);
    }
    status.textContent=isLive?'Authenticated read · current '+data.revision+' · invoices not certified':
      'Historical verified snapshot · '+data.revision+' · current source review flags not verified';
  }
  async function initialize(){
    try{const v2=await fetchJson('data/vendor-bills-status.v2.json');show(v2,true)}
    catch(_){try{show(await fetchJson('data/vendor-bills-status.v1.json'),false)}
      catch(__){status.textContent='Vendor Bills source status unavailable'}}
  }
  initialize();
})();
