"use strict";

(() => {
  const select = selector => document.querySelector(selector);
  const text = value => String(value).replace(/[&<>"']/g, character => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[character]));
  const number = value => Number(value).toLocaleString(undefined, {maximumFractionDigits: 2});
  let data = null;
  let step = 0;
  let timer = null;
  let version = 0;
  let busy = false;
  let heapFrames = [];
  const mode = () => select('#phase3-mode').value;
  const total = () => !data || mode() === 'heatmap' ? 0 : mode() === 'sort' ? data.sort.steps.length : mode() === 'search' ? (data.search?.steps.length || 0) : mode() === 'binary' ? (data.binary?.steps.length || 0) : Math.max(0, heapFrames.length - 1);
  const catalog = () => new Map(data.catalog.map(row => [row.id, row]));

  async function api(path, payload) {
    const response = await fetch(path, payload === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Unable to load Phase 3.');
    return result;
  }

  function pause() {
    clearInterval(timer);
    timer = null;
    select('#phase3-play').textContent = '▶';
    select('#phase3-play').setAttribute('aria-label', 'Play Phase 3 steps');
    select('#phase3-play').title = 'Play steps';
  }

  function options(selector, values, preferred) {
    const element = select(selector);
    const previous = preferred ?? element.value;
    element.innerHTML = values.map(([value, label]) => `<option value="${text(value)}">${text(label)}</option>`).join('');
    if (values.some(([value]) => value === previous)) element.value = previous;
  }

  function controls() {
    select('#phase3-analyze').disabled = busy;
    ['#phase3-metric', '#phase3-category', '#phase3-direction', '#phase3-target', '#phase3-mode'].forEach(selector => { select(selector).disabled = busy; });
    select('#phase3-push').disabled = busy || !data || data.heap.items.length >= 20;
    select('#phase3-pop').disabled = select('#phase3-clear').disabled = busy || !data?.heap.items.length;
    select('#phase3-priority-metric').disabled = busy || !!data?.heap.items.length;
    select('#phase3-food').disabled = busy;
    select('#phase3-prev').disabled = select('#phase3-reset').disabled = busy || step === 0;
    select('#phase3-next').disabled = busy || step >= total();
    select('#phase3-play').disabled = busy || total() === 0;
    select('#phase3-step').disabled = busy || total() === 0;
  }

  function bars(ids, current, checked, mergedRange) {
    const byId = catalog();
    const maximum = Math.max(1, ...data.rows.map(row => row[data.metric]));
    return `<div class="phase3-array" role="list">${ids.map((id, index) => {
      const row = byId.get(id);
      const active = mergedRange && index >= mergedRange.low && index < mergedRange.high;
      const state = index === current ? 'current' : checked.has(index) ? 'visited' : active ? 'pending' : '';
      return `<div class="phase3-array-node ${state}" role="listitem"><small>INDEX ${index}</small><strong>${text(row.name)}</strong><div class="phase3-bar-space"><div style="height:${row[data.metric] / maximum * 100}%"></div></div><span>${number(row[data.metric])}</span></div>`;
    }).join('')}</div>`;
  }

  function heapTree(items) {
    if (!items.length) return '<div class="viz-empty">Priority queue is empty.</div>';
    const labels = catalog();
    const levels = Math.floor(Math.log2(items.length)) + 1;
    const width = Math.max(560, 2 ** (levels - 1) * 180);
    const height = levels * 125 + 20;
    const points = items.map((entry, index) => {
      const depth = Math.floor(Math.log2(index + 1));
      return {entry, index, horizontal: (index - (2 ** depth - 1) + 0.5) * width / 2 ** depth, vertical: depth * 125 + 52};
    });
    const lines = points.slice(1).map(point => {
      const parent = points[Math.floor((point.index - 1) / 2)];
      return `<path d="M${parent.horizontal},${parent.vertical + 36} L${point.horizontal},${point.vertical - 36}"/>`;
    }).join('');
    const nodes = points.map(point => `<foreignObject x="${point.horizontal - 80}" y="${point.vertical - 36}" width="160" height="82"><div xmlns="http://www.w3.org/1999/xhtml" class="phase3-heap-node ${point.index === 0 ? 'current' : ''}"><small>${point.index === 0 ? 'ROOT' : `INDEX ${point.index}`} · #${point.entry.order + 1}</small><strong>${text(labels.get(point.entry.value).name)}</strong><span>${number(point.entry.priority)}</span></div></foreignObject>`).join('');
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" role="img" aria-label="Max-heap priority tree"><title>Array-backed max-heap. Parent index floor((index - 1) / 2).</title><g class="viz-tree-lines">${lines}</g>${nodes}</svg>`;
  }

  function heatmap() {
    if (!data.rows.length) return '<p class="viz-empty">No foods in this category.</p>';
    const abbreviations = ['His', 'Ile', 'Leu', 'Lys', 'Met + Cys', 'Phe + Tyr', 'Thr', 'Trp', 'Val'];
    const headings = data.rows[0].groups.map((group, index) => `<th scope="col"><abbr title="${text(group.name)}">${abbreviations[index]}</abbr></th>`).join('');
    const rows = data.rows.map(row => `<tr><th scope="row">${text(row.name)}</th>${row.groups.map(group => {
      const band = group.coverage < 50 ? 'low' : !group.meets ? 'partial' : group.coverage < 150 ? 'met' : 'high';
      return `<td class="heat-${band}" title="${text(row.name)}: ${text(group.name)}; ${number(group.amount_mg)} mg / ${number(group.target_mg)} mg reference; ${group.meets ? 'meets' : 'below'} pattern">${number(group.coverage)}%</td>`;
    }).join('')}</tr>`).join('');
    return `<table class="phase3-heatmap"><caption>WHO adult reference-pattern coverage (%)</caption><thead><tr><th scope="col">Food</th>${headings}</tr></thead><tbody>${rows}</tbody></table>`;
  }

  function render() {
    if (!data) return;
    step = Math.min(step, total());
    select('#phase3-step').max = total();
    select('#phase3-step').value = step;
    select('#phase3-position').textContent = `${step} / ${total()}`;
    select('#phase3-heap-actions').hidden = mode() !== 'heap';
    select('#phase3-playback').hidden = mode() === 'heatmap';
    select('#phase3-operation').hidden = mode() !== 'heap';
    select('#phase3-heap-array').innerHTML = '';
    const searchFrame = mode() === 'search' && step ? data.search.steps[step - 1] : null;
    select('#phase3-rows').innerHTML = data.rows.map((row, index) => `<tr class="${searchFrame?.index === index ? 'phase3-current-row' : ''}"><td>${index + 1}</td><td><button class="text-button" data-detail="${text(row.id)}">${text(row.name)}</button></td><td>${text(row.category)}</td><td>${number(row[data.metric])}</td><td>${row.met_count} / 9</td></tr>`).join('');
    if (mode() === 'sort') {
      const frame = step ? data.sort.steps[step - 1] : null;
      select('#phase3-status').textContent = frame ? `Merge ${step}: indices ${frame.low}–${frame.middle - 1} and ${frame.middle}–${frame.high - 1}${step === total() ? ' · Sorted' : ''}` : 'Original dataset order';
      select('#phase3-diagram').innerHTML = bars(frame ? frame.items : data.initial, -1, new Set(), frame);
      select('#phase3-complexity').textContent = `Stable merge sort: O(n log n) time, O(n) auxiliary space; ${data.sort.comparisons} comparisons. Full-array teaching frames use O(n²) storage.`;
    } else if (mode() === 'search') {
      select('#phase3-status').textContent = !data.search ? 'Enter a food name above and run Analyze.' : searchFrame ? `${searchFrame.matched ? 'Found' : 'Compared'}: ${data.rows[searchFrame.index].name} · ${step} comparisons${step === total() && !searchFrame.matched ? ' · No exact match in this category' : ''}` : `Ready to search for ${data.target}`;
      select('#phase3-diagram').innerHTML = bars(data.rows.map(row => row.id), searchFrame?.index ?? -1, new Set((data.search?.steps || []).slice(0, step).map(frame => frame.index)), null);
      select('#phase3-complexity').textContent = 'Linear search: O(n) worst-case comparisons, O(1) working space; recorded teaching trace O(n). Searches the ranked results in order.';
    } else if (mode() === 'binary') {
      const frame = step ? data.binary?.steps[step - 1] : null;
      const ids = data.binary?.items || [];
      const found = data.binary?.found;
      select('#phase3-status').textContent = !data.binary ? 'No search name selected.' : frame ? `Low ${frame.low} · Mid ${frame.mid} · High ${frame.high} · ${frame.name}${step === total() ? found ? ' · Found' : ' · No exact match' : ''}` : `Name-sorted array · ${ids.length} foods · Target: ${data.target}`;
      select('#phase3-diagram').innerHTML = bars(ids, frame?.mid ?? -1, new Set((data.binary?.steps || []).slice(0, Math.max(0, step - 1)).map(item => item.mid)), frame ? {low: frame.low, high: frame.high + 1} : null);
      select('#phase3-complexity').textContent = 'Binary search: O(log n) comparisons on a name-sorted array; merge-sort preparation O(n log n). Low/high bound the remaining candidates.';
    } else if (mode() === 'heatmap') {
      select('#phase3-status').textContent = `${data.rows.length} foods · 9 reference groups · Illustrative nutrition data`;
      select('#phase3-diagram').innerHTML = heatmap();
      select('#phase3-heap-array').innerHTML = '<span class="heat-low">Below 50%</span><span class="heat-partial">50% to below pattern</span><span class="heat-met">Meets pattern to below 150%</span><span class="heat-high">150% and above</span>';
      select('#phase3-complexity').textContent = 'Coverage is relative to protein, not daily intake or digestibility. Cysteine and tyrosine are included in their combined reference groups. Percentages are rounded; colors use the unrounded meets-pattern decision.';
    } else {
      const frame = heapFrames[step] || {action: 'Current heap', items: data.heap.items};
      select('#phase3-status').textContent = `${frame.action} · Frame ${step} / ${total()} · Live queue: ${data.heap.items.length} / 20 entries · ${data.metrics[data.heap.metric]}`;
      select('#phase3-diagram').innerHTML = heapTree(frame.items);
      const labels = catalog();
      select('#phase3-heap-array').innerHTML = frame.items.map((entry, index) => `<span><b>[${index}]</b> ${text(labels.get(entry.value).name)} · ${number(entry.priority)} · #${entry.order + 1}</span>`).join('');
      select('#phase3-complexity').textContent = 'Max-heap: insert/extract O(log n), root lookup O(1). Children: 2i+1, 2i+2. Ties: earlier insertion first. Replay frames may show intermediate heap states; full-array trace costs O(n log n) per operation.';
    }
    controls();
  }

  async function load() {
    pause();
    const requestId = ++version;
    busy = true;
    controls();
    select('#phase3-content').hidden = true;
    select('#phase3-error').hidden = true;
    const params = new URLSearchParams({metric: select('#phase3-metric').value, direction: select('#phase3-direction').value, category: select('#phase3-category').value, target: select('#phase3-target').value});
    try {
      const result = await api(`/api/phase3?${params}`);
      if (requestId !== version) return;
      data = result;
      step = 0;
      heapFrames = [{action: 'Current heap', items: data.heap.items}];
      options('#phase3-metric', Object.entries(data.metrics), data.metric);
      options('#phase3-priority-metric', Object.entries(data.metrics), data.heap.metric);
      options('#phase3-category', [['', 'All categories'], ...[...new Set(data.catalog.map(row => row.category))].map(category => [category, category])]);
      options('#phase3-food', data.catalog.map(row => [row.id, row.name]));
      const summary = data.summary;
      select('#phase3-summary').innerHTML = `<div><small>FOODS</small><strong>${summary.count}</strong></div><div><small>MEAN</small><strong>${number(summary.mean)}</strong></div><div><small>MINIMUM</small><strong>${number(summary.minimum)}</strong></div><div><small>MAXIMUM</small><strong>${number(summary.maximum)}</strong></div><p>${text(data.metrics[data.metric])}</p>`;
      select('#phase3-table-caption').textContent = `Merge-sorted by ${data.metrics[data.metric]}`;
      select('#phase3-value-label').textContent = data.metrics[data.metric];
      select('#phase3-search-outcome').textContent = !data.search ? '' : `${data.search.index === null ? 'No exact match' : `Found at rank ${data.search.index + 1}`} · Linear: ${data.search.steps.length} comparisons · Binary: ${data.binary.steps.length} comparisons`;
      select('#phase3-operation').textContent = '';
      select('#phase3-content').hidden = false;
      render();
    } catch (error) {
      if (requestId !== version) return;
      select('#phase3-error').textContent = error.message;
      select('#phase3-error').hidden = false;
    } finally {
      if (requestId === version) { busy = false; controls(); }
    }
  }

  async function mutate(action) {
    if (busy || !data) return;
    pause();
    busy = true;
    controls();
    select('#phase3-error').hidden = true;
    const before = data.heap.items;
    const requestId = version;
    try {
      const result = await api('/api/priority', {action, food_id: select('#phase3-food').value, metric: select('#phase3-priority-metric').value});
      if (requestId !== version) return;
      data.heap = result.heap;
      heapFrames = [{action: 'Before operation', items: before}, ...result.steps];
      step = heapFrames.length - 1;
      select('#phase3-operation').textContent = result.removed ? `Processed ${catalog().get(result.removed.value).name}: priority ${number(result.removed.priority)} · ${number(result.analysis.protein_g)} g protein · ${number(result.analysis.essential_mg)} mg essential amino acids · ${number(result.analysis.score)}% pattern score` : action === 'push' ? 'Food inserted; heap order restored.' : 'Priority queue cleared.';
      render();
    } catch (error) {
      if (requestId !== version) return;
      select('#phase3-error').textContent = error.message;
      select('#phase3-error').hidden = false;
    } finally { if (requestId === version) { busy = false; controls(); } }
  }

  function move(next) { pause(); step = Math.max(0, Math.min(total(), next)); render(); }
  function play() {
    if (timer) return pause();
    if (busy || !total()) return;
    if (step === total()) step = 0;
    select('#phase3-play').textContent = 'Ⅱ';
    select('#phase3-play').title = 'Pause steps';
    select('#phase3-play').setAttribute('aria-label', 'Pause Phase 3 steps');
    timer = setInterval(() => { step++; render(); if (step === total()) pause(); }, Number(select('#phase3-speed').value));
  }
  select('#phase3-analysis-form').addEventListener('submit', event => { event.preventDefault(); if (!busy) load(); });
  select('#phase3-push-form').addEventListener('submit', event => { event.preventDefault(); mutate('push'); });
  select('#phase3-pop').addEventListener('click', () => mutate('pop'));
  select('#phase3-clear').addEventListener('click', () => mutate('clear'));
  select('#phase3-mode').addEventListener('change', () => move(0));
  select('#phase3-reset').addEventListener('click', () => move(0));
  select('#phase3-prev').addEventListener('click', () => move(step - 1));
  select('#phase3-next').addEventListener('click', () => move(step + 1));
  select('#phase3-step').addEventListener('input', event => move(Number(event.target.value)));
  select('#phase3-play').addEventListener('click', play);
  select('#phase3-speed').addEventListener('change', () => { if (timer) { pause(); play(); } });
  document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
  document.addEventListener('aminomatch-view', () => {
    pause();
    ++version;
    busy = false;
    if (currentView === 'phase3' && state) {
      load();
    }
  });
  document.addEventListener('aminomatch-state', () => {
    pause();
    ++version;
    busy = false;
    data = null;
    select('#phase3-category').value = '';
    if (currentView === 'phase3') load();
  });
  if (state && currentView === 'phase3') load();
})();