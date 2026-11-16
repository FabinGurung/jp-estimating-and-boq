(() => {
  'use strict';
  const root = document.getElementById('contractor-bills-status');
  if (!root) return;
  const status = root.querySelector('[data-contractor-status]');
  const counts = {
    sourceTabs: 'Original source tabs',
    sourceRows: 'Indexed source rows',
    claimRows: 'Claim summaries',
    workRows: 'Primary work lines',
    historicalRows: 'Non-additive history rows',
    comparisonRows: 'Reconciliations',
    reviewFlags: 'Unresolved reviews',
    approvedClaims: 'Certified claims'
  };
  fetch('data/contractor-bills-status.v1.json', {cache: 'no-store'})
    .then(r => { if (!r.ok) throw new Error('Status unavailable'); return r.json(); })
    .then(data => {
      if (data.schema !== 'jp.contractor-bills-status.v1' ||
          !/^V[0-9]{6}$/.test(data.revision) ||
          !/^V[0-9]{6}$/.test(data.normalizedDataRevision) ||
          !['VERIFIED_SNAPSHOT','MANUAL_AUTHENTICATED_READ'].includes(data.sourceMode) ||
          Object.keys(counts).some(k => !Number.isSafeInteger(data[k]) || data[k] < 0))
        throw new Error('Status contract invalid');
      const number = new Intl.NumberFormat('en-IN');
      const list = root.querySelector('dl');
      list.replaceChildren();
      for (const [key, label] of Object.entries(counts)) {
        const group = document.createElement('div');
        const dt = document.createElement('dt');
        const dd = document.createElement('dd');
        dt.textContent = label;
        dd.textContent = number.format(data[key]);
        group.append(dt, dd);
        list.append(group);
      }
      const mode = data.sourceMode === 'MANUAL_AUTHENTICATED_READ' ? 'Manual source read' : 'Verified snapshot';
      status.textContent = `${mode} · ${data.revision} · normalized data ${data.normalizedDataRevision}`;
    })
    .catch(() => { status.textContent = 'Contractor Bills status temporarily unavailable.'; });
})();