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
    core=[dict(key=k,title=t,cards=cards(e)) for k,t,e in WORKBOOK_GROUPS]
    quantity=[dict(key='bbs',title='BBS',cards=cards([('bbs-slab','Slab BBS',''),('bbs-beam','Beam BBS',''),('bbs-shear','Shear Wall BBS',''),('bbs-stair','Staircase BBS','')])),
              dict(key='quantity',title='Measurement',cards=cards([('field-1','Measurement','')]))]
    payloads={'estimating-workbook-links.json':dict(schema='jp.estimating.workbook-links.v1',groups=core),
        'quantity-workbook-links.json':dict(groups=quantity),
        'estimating-project-directory.json':dict(schema='jp.estimating.project-directory.v1',groups=[],readAtUtc='2026-11-24T00:00:00Z'),
        'estimating-source-receipt.json':dict(reinforcement=[dict(item=x,sourceRead=True) for x in ['Slab','Beam','Shear wall','Staircase']])}
    for name,value in payloads.items():
        (data/name).write_text(json.dumps(value))
    (site/'measurements-boq.html').write_text('Archived')
    (site/'projects').mkdir()
    (site/'projects'/'old.html').write_text('Archived')
    stage(site)
    assert len(json.loads((data/'home-links.json').read_text())['groups'])==5
    assert sum(len(g['cards']) for g in json.loads((data/'home-links.json').read_text())['groups'])==38
    assert sum(len(g['cards']) for g in json.loads((data/'rates-links.json').read_text())['groups'])==2
    assert 'N / PAGE' not in (site/'index.html').read_text()
    assert 'W / SECTIONS' not in (site/'index.html').read_text()
    assert 'source-gallery.js' not in (site/'index.html').read_text()
    assert not (site/'measurements-boq.html').exists()
    assert not (site/'projects').exists()
print('Compact portal fixture: 38 links, 2 rates only, archived routes removed, single navigation.')
