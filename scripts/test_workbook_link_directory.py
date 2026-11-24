"""Offline regression for the explicitly approved original-workbook navigation."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import sync_estimation_sources as source


def test_directory():
    entries = [item for _, _, group in source.WORKBOOK_GROUPS for item in group]
    assert len(entries) == 33
    registry = {
        key: (f'fixture-workbook-{i:030d}', '', mode)
        for i, (key, _, _, mode) in enumerate(entries, 1)
    }
    ordered_ids = [registry[key][0] for key, *_ in entries]

    def must_hold(site, candidate):
        try:
            source.publish_workbook_links(candidate, site)
        except (source.SourceHold, KeyError):
            return
        raise AssertionError('Unapproved source contract was accepted')

    with TemporaryDirectory() as tmp:
        site = Path(tmp)
        (site / 'data').mkdir()
        must_hold(site, registry)  # Synthetic IDs are not the owner's approved IDs.
        assert not (site / 'data/estimating-workbook-links.json').exists()
        pinned = source.APPROVED_WORKBOOK_ID_DIGEST
        try:
            source.APPROVED_WORKBOOK_ID_DIGEST = hashlib.sha256('\n'.join(ordered_ids).encode()).hexdigest()
            source.publish_workbook_links(registry, site)
            payload = json.loads((site / 'data/estimating-workbook-links.json').read_text())
            assert payload['schema'] == 'jp.estimating.workbook-links.v1'
            assert [g['key'] for g in payload['groups']] == ['core', 'wages', 'workforce']
            assert [len(g['cards']) for g in payload['groups']] == [7, 4, 21]
            cards = [c for g in payload['groups'] for c in g['cards']]
            assert len({c['url'] for c in cards}) == 32
            assert all(c['key'] != 'funding' for c in cards)
            assert all(set(c) == {'key', 'title', 'detail', 'url'} for c in cards)
            assert [c['title'] for c in payload['groups'][2]['cards']] == [f'W{i:02}' for i in range(1, 22)]
            changed = dict(registry)
            changed['w01'] = ('different-workbook-id-0000000000', '', registry['w01'][2])
            must_hold(site, changed)
            changed = dict(registry)
            changed['historical-wage'] = (registry['historical-wage'][0], '', 'Finance reader')
            must_hold(site, changed)
        finally:
            source.APPROVED_WORKBOOK_ID_DIGEST = pinned
    print('CURVED WORKBOOK LINKS PASS: 8 + 4 + 21 originals; unique links, key-only workforce labels, identity and mode guards.')


if __name__ == '__main__':
    test_directory()
