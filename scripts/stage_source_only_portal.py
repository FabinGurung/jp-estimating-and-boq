#!/usr/bin/env python3
"""Produce only the user-approved working-source portal; preserve historic code in Git."""
import argparse
import html
import json
from pathlib import Path
import re
import shutil
import tempfile

ROOT=Path(__file__).resolve().parents[1]
NAV=[('index.html','Home'),('rate-sources.html','Rates'),('projects.html','Projects'),
     ('quantity-workbooks.html','Quantity workbooks'),('finance.html','Registers')]
ESC=html.escape
CSS="""
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f6f7f3;color:#183b31;font:16px/1.5 system-ui,-apple-system,sans-serif}a{color:#146344}header{background:#17382f;color:white;padding:14px max(16px,calc((100vw - 1100px)/2));position:sticky;top:0;z-index:200}header strong{font-size:1.05rem;letter-spacing:.06em}nav{display:flex;gap:6px;overflow-x:auto;white-space:nowrap;margin-top:10px;scrollbar-width:thin}nav a{color:#fff;padding:9px 12px;border-radius:8px;text-decoration:none;font-size:.88rem;font-weight:650}nav a[aria-current=page]{background:#e5e9d8;color:#17382f}main{max-width:1100px;margin:auto;padding:24px 16px 40px;min-width:0}h1{font-size:clamp(1.65rem,4vw,2.4rem);margin:0 0 7px;line-height:1.2}h2{font-size:1.2rem;margin:0 0 10px}.sub{color:#586d61;margin:0 0 18px}.org{margin:20px 0}.project-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,265px),1fr));gap:12px}.project{background:white;border:1px solid #d3ddd5;border-radius:13px;padding:16px;min-width:0}.project h3{margin:0 0 10px;font-size:1.08rem}.source-row{padding:10px 0;border-top:1px solid #e3e9e4;font-size:.9rem}.source-row a{font-weight:650}.source-row strong{display:block;font-variant-numeric:tabular-nums;margin:3px 0}.source-row small{display:block;color:#647568}.caption{font-size:.85rem;color:#607166}.footer{margin-top:18px;border-top:1px solid #d4ddd4;padding-top:14px;font-size:.85rem}button,a{touch-action:manipulation}a:focus-visible,button:focus-visible{outline:3px solid #558f75;outline-offset:3px}
@media(max-width:600px){header{position:static;padding:12px 14px}main{padding:20px 12px}nav{gap:3px}nav a{padding:8px 10px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
"""
PROJECTS_JS=r"""
(() => {
 const root=document.getElementById('projectDirectory');
 if(!root)return;
 const add=(tag,p,t,c)=>{const e=document.createElement(tag);if(t)e.textContent=t;if(c)e.className=c;p.append(e);return e;};
 const npr=new Intl.NumberFormat('en-IN',{style:'currency',currency:'NPR',minimumFractionDigits:0,maximumFractionDigits:2});
 const labels={'Fabin Gurung payments':'finance-4','Krishna Kumar Gupta payments':'finance-5','Vendor Bills':'finance-3','Contractor Bills':'finance-2'};
 Promise.all(['data/estimating-project-directory.json','data/estimating-workbook-links.json'].map(url=>fetch(url,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json()}))).then(([data,links])=>{
  if(data.schema!=='jp.estimating.project-directory.v1'||!Array.isArray(data.groups))throw Error();
  const urls=new Map(links.groups.flatMap(g=>g.cards.map(c=>[c.key,c.url])));
  root.replaceChildren();
  add('p',root,'Source read: '+new Date(data.readAtUtc).toLocaleString('en-GB',{timeZone:'Asia/Kathmandu'})+' NPT','caption');
  for(const group of data.groups){
   if(!group.projects.length)continue;
   const section=add('section',root,null,'org');add('h2',section,group.organization);
   const grid=add('div',section,null,'project-grid');
   for(const p of group.projects){
    if(!p.sources.length)continue;
    const card=add('article',grid,null,'project');add('h3',card,p.name);
    for(const src of p.sources){
     const row=add('div',card,null,'source-row');
     const link=add('a',row,src.source);link.href=urls.get(labels[src.source]);link.target='_blank';link.rel='noopener noreferrer';
     if(typeof src.detail?.recordedNpr==='number'&&Number.isFinite(src.detail.recordedNpr))add('strong',row,npr.format(src.detail.recordedNpr));
     if(src.detail?.state)add('small',row,src.detail.state);
    }
   }
  }
 }).catch(()=>{root.textContent='Project source directory unavailable. Open the original working registers.';});
})();
"""
def read(path):
    return json.loads(path.read_text(encoding='utf-8'))
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def page(path,title,subtitle,body):
    nav=''.join(f'<a href="{u}"'+(' aria-current="page"' if u==path else '')+f'>{ESC(label)}</a>' for u,label in NAV)
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{ESC(title)} | JP Estimating</title><link rel="stylesheet" href="portal.css"><script defer src="portal-carousels.js"></script><script defer src="portal-projects.js"></script></head><body><header><strong>JP ESTIMATING &amp; BOQ</strong><nav aria-label="Main navigation">{nav}</nav></header><main><h1>{ESC(title)}</h1><p class="sub">{ESC(subtitle)}</p>{body}<p class="footer"><a href="https://docs.google.com/spreadsheets/d/12TvdU4pI_qiTPCe1JGkc1pn1QzKqwLSIS79QUk4ATEY/edit">Source Index</a> · <a href="https://drive.google.com/drive/folders/126AVR4iacXV3bwK8St66QrUFrYqlRtWS">Estimating Drive</a></p></main></body></html>'
def stage(site):
    directory=read(site/'data/estimating-workbook-links.json')
    quantity=read(site/'data/quantity-workbook-links.json')
    project=read(site/'data/estimating-project-directory.json')
    receipt=read(site/'data/estimating-source-receipt.json')
    groups=directory['groups']+quantity['groups']
    assert [len(g['cards']) for g in groups]==[8,4,21,6,1]
    cards=[c for g in groups for c in g['cards']]
    assert len({c['key'] for c in cards})==40 and len({c['url'] for c in cards})==40
    assert all(re.fullmatch(r'https://docs\.google\.com/spreadsheets/d/[A-Za-z0-9_-]{20,160}/edit',c['url']) for c in cards)
    assert all(set(c)=={'key','title','detail','url'} for c in cards)
    assert all(re.fullmatch(r'W(?:0[1-9]|1[0-9]|2[01])',c['title']) for c in groups[2]['cards'])
    statuses={r['item']:r['sourceRead'] for r in receipt['reinforcement']}
    for c in groups[3]['cards']:
        item=c['title'].replace(' BBS','')
        flag=statuses.get(item) if item!='Shear Wall' else statuses.get('Shear wall')
        c['detail']='Source read verified; engineering approval separate' if flag is True else 'Registered original; source read not confirmed'
        if c['key'] in ('bbs-footing','bbs-column'):
            c['detail'] += '; open workbook for procurement readiness'
    def select(key,title,cards):
        return {'key':key,'title':title,'cards':cards}
    core=groups[0]['cards']
    rates=select('rates','Rate workbooks',core[:2])
    finance=select('finance','Payments, bills and funding',core[2:])
    variants={'home':groups,'rates':[rates],'registers':[finance,groups[1],groups[2]],'quantity':groups[3:]}
    oldjs=(ROOT/'estimating-workbook-carousels.js').read_text()
    js=oldjs.replace("const expected = [['core',8],['wages',4],['workforce',21]];",
      "const expected = JSON.parse(root.dataset.expected);")
    js=js.replace("data.groups.length!==3","data.groups.length!==expected.length")
    js=js.replace("fetch('data/estimating-workbook-links.json',{cache:'no-store'})","fetch(root.dataset.json,{cache:'no-store'})")
    assert 'root.dataset.json' in js and 'root.dataset.expected' in js
    def gallery(key):
        expected=json.dumps([[g['key'],len(g['cards'])] for g in variants[key]],separators=(',',':'))
        return f'<section id="registeredWorkbookLinks"><div id="approvedWorkbookGalleries" data-json="data/{key}-links.json" data-expected="{ESC(expected,quote=True)}"><p data-workbook-loading>Loading working Google Sheets…</p></div></section>'
    pages={
      'index.html':page('index.html','Working Google Sheets','40 original workbook links: 33 registers and rate/funding references, 6 BBS and 1 work measurement source.',gallery('home')),
      'rate-sources.html':page('rate-sources.html','Rates','Open the working rate libraries in Google Sheets.',gallery('rates')),
      'quantity-workbooks.html':page('quantity-workbooks.html','Quantity workbooks','BBS and measurement sources. Engineering approval remains separate.',gallery('quantity')),
      'finance.html':page('finance.html','Working registers','Payments, bills, wages, attendance and workforce records.',gallery('registers')),
      'projects.html':page('projects.html','Projects by organization','Recorded source summaries. Payments and claims are separate; candidate mappings are not approvals.','<div id="projectDirectory"><p>Loading project records…</p></div>'),
      'source-sheets.html':'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=index.html#registeredWorkbookLinks"><title>Working Google Sheets</title></head><body><a href="index.html#registeredWorkbookLinks">Open the workbook galleries</a></body></html>'
    }
    with tempfile.TemporaryDirectory() as tmp:
        out=Path(tmp)
        for path,body in pages.items():
            (out/path).write_text(body,encoding='utf-8')
        (out/'portal.css').write_text(CSS,encoding='utf-8')
        (out/'portal-carousels.js').write_text(js,encoding='utf-8')
        (out/'portal-projects.js').write_text(PROJECTS_JS,encoding='utf-8')
        for key,variant in variants.items():
            write(out/'data'/f'{key}-links.json',{'schema':directory['schema'],'groups':variant})
        write(out/'data/estimating-workbook-links.json',directory)
        write(out/'data/estimating-project-directory.json',project)
        # Preserve only the previously approved manual-source receipt files for future manual refreshes.
        for name in ('vendor-bills-status.v1.json','vendor-bills-status.v2.json','contractor-bills-status.v1.json','income-register-status.v1.json'):
            p=site/'data'/name
            if p.is_file():
                shutil.copy2(p,out/'data'/name)
        # Strict allowlist: the old 72-page website and all legacy knowledge assets are NOT published.
        for child in site.iterdir():
            if child.is_dir():shutil.rmtree(child)
            else:child.unlink()
        shutil.copytree(out,site,dirs_exist_ok=True)
    assert sorted(p.name for p in site.glob('*.html'))==sorted(pages)
    assert not (site/'measurements-boq.html').exists()
    assert not (site/'projects').exists()
    assert len(list(site.rglob('*.html')))==6
    print('SOURCE-ONLY PORTAL PASS: 5 working routes + source-directory redirect; 40 original links; old pages excluded.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--site',required=True,type=Path);stage(p.parse_args().site)
