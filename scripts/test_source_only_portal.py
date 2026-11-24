#!/usr/bin/env python3
"""Test the compact portal without access to private Drive."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from stage_source_only_portal import stage
from sync_estimation_sources import WORKBOOK_GROUPS

with TemporaryDirectory() as tmp:
    site=Path(tmp)
    data=site/'data'
    data.mkdir()
    n=0
    def cards(entries):
        global n
        out=[]
        for key,title,detail,*_ in entries:
            n+=1
            out.append(dict(key=key,title=title,detail=detail,url=f'https://docs.google.com/spreadsheets/d/fixture-{n:030d}/edit'))
        return out
    core=[dict(key=k,title=t,cards=cards([item for item in e if item[3] != 'Archived'])) for k,t,e in WORKBOOK_GROUPS]
    quantity=[dict(key='bbs',title='BBS',cards=cards([('bbs-slab','Slab BBS',''),('bbs-beam','Beam BBS',''),('bbs-shear','Shear Wall BBS',''),('bbs-stair','Staircase BBS',''),('bbs-footing','Footing BBS',''),('bbs-column','Column BBS',''),('bbs-water-tank','Water Tank BBS','')])),
              dict(key='quantity',title='Measurement',cards=cards([('field-1','Measurement','')]))]
    payloads={'estimating-workbook-links.json':dict(schema='jp.estimating.workbook-links.v1',groups=core),
        'quantity-workbook-links.json':dict(groups=quantity),
        'estimating-project-directory.json':dict(schema='jp.estimating.project-directory.v1',groups=[],readAtUtc='2026-11-24T00:00:00Z'),
        'estimating-source-receipt.json':dict(reinforcement=[dict(item=x,sourceRead=True) for x in ['Slab','Beam','Shear wall','Staircase','Footing','Column','Water Tank']])}
    for name,value in payloads.items():
        (data/name).write_text(json.dumps(value))
    (site/'measurements-boq.html').write_text('Archived')
    (site/'projects').mkdir()
    (site/'projects'/'old.html').write_text('Archived')
    stage(site)
    assert len(json.loads((data/'home-links.json').read_text())['groups'])==5
    assert sum(len(g['cards']) for g in json.loads((data/'home-links.json').read_text())['groups'])==40
    assert sum(len(g['cards']) for g in json.loads((data/'rates-links.json').read_text())['groups'])==2
    assert {c['key'] for g in json.loads((data/'quantity-links.json').read_text())['groups'] for c in g['cards']} >= {'bbs-column','bbs-footing','bbs-water-tank'}
    assert any(c['key']=='bbs-water-tank' and 'no purchase release' in c['detail'] for g in json.loads((data/'quantity-links.json').read_text())['groups'] for c in g['cards'])
    assert 'id="homeOverview"' in (site/'index.html').read_text()
    assert 'id="approvedWorkbookGalleries"' not in (site/'index.html').read_text()
    assert 'id="registerDirectory"' in (site/'finance.html').read_text()
    assert 'id="approvedWorkbookGalleries"' not in (site/'finance.html').read_text()
    assert 'id="rateEvidence"' in (site/'rate-sources.html').read_text()
    assert (data/'contractor-summary-v0.1/page-005.jpg').is_file()
    assert len(json.loads((data/'contractor-work-items.v0.1.json').read_text())['items'])==158
    for page in ('index.html','rate-sources.html','projects.html','quantity-workbooks.html','finance.html'):
        html=(site/page).read_text()
        assert 'class="mascot-lane"' not in html
        assert html.count('class="mascot-track"') == 1
        assert html.count('class="motion-toggle"') == 1
    css=(site/'portal.css').read_text()
    assert '@keyframes calc-free-flight' in css
    assert '.mascot-track{position:fixed;inset:0' in css
    assert 'var(--fly-bottom)' in css and 'var(--fly-middle)' in css
    assert 'pointer-events:none' in css
    assert 'N / PAGE' not in (site/'index.html').read_text()
    assert 'W / SECTIONS' not in (site/'index.html').read_text()
    assert 'source-gallery.js' not in (site/'index.html').read_text()
    assert not (site/'measurements-boq.html').exists()
    assert not (site/'projects').exists()
print('Compact portal fixture: 40 links, 2 rates only, archived routes removed, single navigation.')
