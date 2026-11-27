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
              dict(key='concrete',title='Concrete QTO',cards=cards([(f'concrete-{key}',key+' concrete','Planning only') for key in ('slab','beam','shear','stair','footing','column','water-tank')])),
              dict(key='quantity',title='Measurement',cards=cards([('project-materials','Project materials','Manual snapshot'),('field-1','Measurement','')]))]
    payloads={'estimating-workbook-links.json':dict(schema='jp.estimating.workbook-links.v1',groups=core),
        'quantity-workbook-links.json':dict(groups=quantity),
        'estimating-project-directory.json':dict(schema='jp.estimating.project-directory.v1',groups=[],readAtUtc='2026-11-24T00:00:00Z'),
        'estimating-source-receipt.json':dict(reinforcement=[dict(item=x,sourceRead=True) for x in ['Slab','Beam','Shear wall','Staircase','Footing','Column','Water Tank']])}
    payloads['clean-wage-summaries.json'] = dict(schema='jp.clean-wage-summaries.v1', sections=[], readAtUtc='2026-11-25T00:00:00Z')
    for kind in ('vendors','contractors'):
        url='https://docs.google.com/spreadsheets/d/fixture-'+('v' if kind=='vendors' else 'c')*30+'/edit'
        record=dict(name='Fixture Vendor' if kind=='vendors' else 'Fixture Contractor',url=url+'#gid=123')
        if kind=='contractors':
            record['project']='Fixture Project'
        payloads[f'{kind}-directory.json']=dict(schema='jp.business-directory.v1',kind=kind,source='AUTHENTICATED_SHEET_READ',readAtUtc='2026-11-27T00:00:00Z',registerUrl=url,records=[record])
    for name,value in payloads.items():
        (data/name).write_text(json.dumps(value))
    (site/'measurements-boq.html').write_text('Archived')
    (site/'projects').mkdir()
    (site/'projects'/'old.html').write_text('Archived')
    stage(site)
    assert len(json.loads((data/'home-links.json').read_text())['groups'])==6
    assert sum(len(g['cards']) for g in json.loads((data/'home-links.json').read_text())['groups'])==48
    assert sum(len(g['cards']) for g in json.loads((data/'rates-links.json').read_text())['groups'])==2
    assert {c['key'] for g in json.loads((data/'quantity-links.json').read_text())['groups'] for c in g['cards']} >= {'bbs-column','bbs-footing','bbs-water-tank'}
    assert any(c['key']=='bbs-water-tank' and 'no purchase release' in c['detail'] for g in json.loads((data/'quantity-links.json').read_text())['groups'] for c in g['cards'])
    assert any(g['key']=='concrete' and len(g['cards'])==7 for g in json.loads((data/'quantity-links.json').read_text())['groups'])
    assert "group.key==='concrete'" in (site/'portal-carousels.js').read_text()
    assert 'id="homeOverview"' in (site/'index.html').read_text()
    assert 'id="approvedWorkbookGalleries"' not in (site/'index.html').read_text()
    assert 'id="registerDirectory"' in (site/'finance.html').read_text()
    assert 'id="wageSummaries"' in (site/'finance.html').read_text()
    assert (data/'clean-wage-summaries.json').is_file()
    assert (site/'particle-study.html').is_file()
    assert 'View all ' not in (site/'portal-directory.js').read_text()
    assert 'Work keyword category' in (site/'portal-rate-evidence.js').read_text()
    assert 'id="approvedWorkbookGalleries"' not in (site/'finance.html').read_text()
    assert 'id="rateEvidence"' in (site/'rate-sources.html').read_text()
    assert (data/'contractor-summary-v0.1/page-005.jpg').is_file()
    assert len(json.loads((data/'contractor-work-items.v0.1.json').read_text())['items'])==158
    assert 'Fixture Vendor' in (site/'vendors.html').read_text()
    assert 'Fixture Contractor' in (site/'contractors.html').read_text()
    assert 'Fixture Vendor' not in (site/'finance.html').read_text()
    for page in ('index.html','rate-sources.html','projects.html','quantity-workbooks.html','finance.html','vendors.html','contractors.html'):
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
    assert len(json.loads((data/'quantity-links.json').read_text())['groups']) == 2
    assert 'Measured site work — Fishtail' in (site/'quantity-workbooks.html').read_text()
    assert 'Open CLEAN work measurement register' in (site/'quantity-workbooks.html').read_text()
    assert 'source-gallery.js' not in (site/'index.html').read_text()
    assert not (site/'measurements-boq.html').exists()
    assert not (site/'projects').exists()
print('Compact portal fixture: 48 links, 2 rates only, archived routes removed, single navigation.')
