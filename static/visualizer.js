"use strict";

(() => {
  let result = null;
  let step = 0;
  let timer = null;
  let requestVersion = 0;
  let listMessage = '';
  let processedJob = null;
  const topic = () => $('#viz-topic').value;
  const names = () => new Map(state.foods.map(food => [food.id, food.name]));
  const limit = () => !result ? 0 : topic() === 'tree' ? result.traversal.length : topic() === 'bfs' ? result.bfs.order.length : topic() === 'list' ? result.practice_linked.length : 0;

  function pause() {
    clearInterval(timer);
    timer = null;
    $('#viz-play').textContent = '▶';
    $('#viz-play').setAttribute('aria-label', 'Play traversal');
    $('#viz-play').title = 'Play traversal';
  }

  function sequence(values, visitedCount) {
    return values.map((value, index) => `<span class="${index === visitedCount - 1 ? 'current' : index < visitedCount ? 'visited' : ''}"><b>${index + 1}</b> ${escapeHTML(value)}</span>`).join('');
  }

  function nodeClass(value, order) {
    const index = order.indexOf(value);
    return index >= 0 && index < step ? index === step - 1 ? 'current' : 'visited' : '';
  }

  function treeDiagram() {
    const positions = [];
    const edges = [];
    let column = 0;
    function place(node, depth) {
      if (!node) return null;
      const left = place(node.left, depth + 1);
      const point = { name: node.name, x: column++ * 162 + 85, y: depth * 115 + 48 };
      positions.push(point);
      const right = place(node.right, depth + 1);
      for (const child of [left, right]) if (child) edges.push([point, child]);
      return point;
    }
    place(result.tree, 0);
    const width = Math.max(340, column * 162 + 8);
    const height = Math.max(...positions.map(point => point.y), 48) + 58;
    const lines = edges.map(([parent, child]) => `<path d="M${parent.x},${parent.y + 32} V${parent.y + 55} H${child.x} V${child.y - 32}"/>`).join('');
    const nodes = positions.map(point => `<foreignObject x="${point.x - 73}" y="${point.y - 32}" width="146" height="70"><div xmlns="http://www.w3.org/1999/xhtml" class="viz-tree-node ${nodeClass(point.name, result.traversal)}"><span>${escapeHTML(point.name)}</span></div></foreignObject>`).join('');
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" role="img" aria-label="Food binary search tree"><title>Food binary search tree. Highlighted nodes follow the selected Python traversal.</title><g class="viz-tree-lines">${lines}</g>${nodes}</svg>`;
  }

  function graphDiagram(frame) {
    const ids = Object.keys(result.graph);
    const size = Math.max(580, ids.length * 25);
    const radius = size / 2 - 48;
    const positions = new Map(ids.map((id, index) => {
      const angle = 2 * Math.PI * index / ids.length - Math.PI / 2;
      return [id, { x: size / 2 + Math.cos(angle) * radius, y: size / 2 + Math.sin(angle) * radius, number: index + 1 }];
    }));
    const discovery = new Set(result.bfs.discovery_edges.map(edge => edge.join('|')));
    const visited = new Set(result.bfs.order.slice(0, step));
    const labels = names();
    const edges = ids.flatMap(id => result.graph[id].filter(neighbor => positions.get(id).number < positions.get(neighbor).number).map(neighbor => {
      const first = positions.get(id), second = positions.get(neighbor);
      const reached = visited.has(id) || visited.has(neighbor);
      const isDiscovery = reached && (discovery.has(`${id}|${neighbor}`) || discovery.has(`${neighbor}|${id}`));
      return `<line x1="${first.x}" y1="${first.y}" x2="${second.x}" y2="${second.y}" class="${isDiscovery ? 'discovery' : ''}"/>`;
    })).join('');
    const nodes = ids.map(id => {
      const point = positions.get(id);
      const status = id === frame.current ? 'current' : visited.has(id) ? 'visited' : frame.queue.includes(id) ? 'pending' : '';
      return `<g class="viz-graph-node ${status}"><title>${escapeHTML(labels.get(id))}</title><circle cx="${point.x}" cy="${point.y}" r="23"/><text x="${point.x}" y="${point.y + 5}">${point.number}</text></g>`;
    }).join('');
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" role="img" aria-label="Undirected food pairing graph"><title>Numbered foods correspond to the adjacency list below. Dark lines are BFS discovery edges.</title><g class="viz-graph-edges">${edges}</g>${nodes}</svg>`;
  }

  function mealLabel(meal) {
    const labels = names();
    return meal.length ? meal.map(portion => `${escapeHTML(labels.get(portion.food_id))} (${format(portion.grams)} g)`).join(' + ') : 'Empty meal';
  }

  function render() {
    if (!result) return;
    const selected = topic();
    const total = limit();
    step = Math.min(step, total);
    $('#viz-position').textContent = `${step} / ${total}`;
    $('#viz-step').max = total;
    $('#viz-step').value = step;
    $('#viz-prev').disabled = $('#viz-reset').disabled = step === 0;
    $('#viz-next').disabled = step === total;
    $('#viz-play').disabled = total === 0;
    $('#viz-playback').hidden = ['stack', 'queue'].includes(selected);
    $('#viz-stack-actions').hidden = !['stack', 'queue'].includes(selected);
    $('#viz-pop').hidden = selected !== 'stack';
    $('#viz-list-actions').hidden = selected !== 'list';
    $('#viz-queue-actions').hidden = selected !== 'queue';
    $('#viz-pop').disabled = !state.undo_count;
    $('#viz-push').disabled = state.meal.length >= 30 || state.undo_count >= 200;
    $('#viz-sequence').innerHTML = '';
    $('#viz-details').innerHTML = '';
    if (selected === 'tree') {
      const rules = { inorder: 'Left → Root → Right', preorder: 'Root → Left → Right', postorder: 'Left → Right → Root' };
      $('#viz-status').textContent = `${rules[$('#viz-order').value]} · ${step ? `Visit ${step}: ${result.traversal[step - 1]}` : 'Ready at the beginning'}${step === total ? ' · Complete' : ''}`;
      $('#viz-diagram').innerHTML = treeDiagram();
      $('#viz-sequence').innerHTML = sequence(result.traversal, step);
    } else if (selected === 'bfs') {
      const frame = result.bfs.steps[step];
      const labels = names();
      const ids = Object.keys(result.graph);
      const discovered = frame.discovered.map(id => labels.get(id));
      $('#viz-status').textContent = `${frame.current ? `Visited ${labels.get(frame.current)}` : `Start: ${labels.get(result.bfs.order[0])}`} · Newly queued: ${discovered.join(', ') || 'none'}${step === total ? ` · Complete: ${total} of ${ids.length} foods reachable` : ''}`;
      $('#viz-diagram').innerHTML = graphDiagram(frame);
      $('#viz-sequence').innerHTML = sequence(result.bfs.order.map(id => labels.get(id)), step);
      $('#viz-details').innerHTML = `<h2>BFS queue <small>front → back</small></h2><div class="viz-queue">${frame.queue.length ? frame.queue.map(id => `<span>${escapeHTML(labels.get(id))}</span>`).join('<b aria-hidden="true">→</b>') : '<span>Empty</span>'}</div><h2>Adjacency list</h2><p class="small-note">Each row lists direct connections. Repeated discoveries are skipped; disconnected foods are not visited. Pairing edges use illustrative food data, not dietary recommendations.</p><div class="viz-adjacency">${ids.map((id, index) => `<div class="${id === frame.current ? 'current' : ''}"><strong>${index + 1}. ${escapeHTML(labels.get(id))}</strong><span>→ ${result.graph[id].map(neighbor => `${ids.indexOf(neighbor) + 1}. ${escapeHTML(labels.get(neighbor))}`).join(' · ') || 'No connections'}</span></div>`).join('')}</div>`;
    } else if (selected === 'list') {
      const values = result.practice_linked;
      $('#viz-status').textContent = listMessage || (step ? `Index ${step - 1}: ${values[step - 1]}${step === total ? ' · Next is None (end)' : ''}` : `${total} practice nodes · Head: ${total ? 'index 0' : 'None'} · Tail: ${total ? `index ${total - 1}` : 'None'}`);
      $('#viz-diagram').innerHTML = `<div class="viz-linked">${values.map((name, index) => `<div class="viz-list-node ${index === step - 1 ? 'current' : index < step ? 'visited' : ''}"><small>${index === 0 ? 'HEAD · ' : ''}${index === total - 1 ? 'TAIL · ' : ''}INDEX ${index}</small><strong>${escapeHTML(name)}</strong><span>next →</span></div><b aria-hidden="true">→</b>`).join('')}<span>None</span></div>`;
      $('#viz-sequence').innerHTML = sequence(values, step);
      listFields();
    } else if (selected === 'queue') {
      $('#viz-status').textContent = `FIFO: first in, first out · ${state.queue.length} / 20 saved meals`;
      $('#viz-diagram').innerHTML = `<div class="viz-linked">${state.queue.map((job, index) => `<div class="viz-list-node ${index === 0 ? 'current' : ''}"><small>${index === 0 ? 'FRONT · ' : ''}${index === state.queue.length - 1 ? 'REAR · ' : ''}JOB #${job.id}</small><strong>${job.portions} portions</strong><span>next →</span></div><b aria-hidden="true">→</b>`).join('')}<span>${state.queue.length ? 'None' : 'Front = Rear = None'}</span></div>`;
      $('#viz-details').innerHTML = `<h2>Current meal</h2><p class="viz-current-meal">${mealLabel(state.meal)}</p>`;
      if (processedJob) $('#viz-details').innerHTML += `<h2>Dequeued job #${processedJob.id}</h2><p>${format(processedJob.analysis.protein_g)} g protein · ${format(processedJob.analysis.essential_mg, 0)} mg essential amino acids · ${format(processedJob.analysis.score)}% pattern score</p>`;
      $('#viz-enqueue').disabled = !state.meal.length || state.queue.length >= 20;
      $('#viz-dequeue').disabled = !state.queue.length;
    } else {
      $('#viz-status').textContent = `LIFO: last in, first out · ${result.history.length} previous meal states · Push on meal edit, pop on undo`;
      $('#viz-diagram').innerHTML = `<div class="viz-stack-layout"><div><h2>Undo stack</h2><div class="viz-stack">${result.history.length ? result.history.map((meal, index) => `<div class="viz-stack-node ${index === 0 ? 'current' : ''}"><small>${index === 0 ? 'TOP · next to pop' : `Saved state ${result.history.length - index}`}</small><strong>${mealLabel(meal)}</strong></div>`).join('') : '<p>No saved states yet. Adding a food pushes the previous meal onto this stack.</p>'}</div><p class="small-note">Bottom: oldest saved state. Viewing the stack does not remove anything.</p></div><div><h2>Current meal</h2><p class="viz-current-meal">${mealLabel(state.meal)}</p></div></div>`;
    }
  }

  async function load() {
    pause();
    const version = ++requestVersion;
    result = null;
    step = 0;
    listMessage = '';
    $('#viz-content').hidden = true;
    $('#viz-content').setAttribute('aria-busy', 'true');
    $('#viz-error').hidden = true;
    const selected = topic();
    $('#viz-order-field').hidden = selected !== 'tree';
    $('#viz-start-field').hidden = selected !== 'bfs';
    const options = state.foods.map(food => [food.id, food.name]);
    populateSelect('#viz-start', options);
    populateSelect('#viz-food', options);
    try {
      const params = new URLSearchParams({ order: $('#viz-order').value, start: $('#viz-start').value });
      const data = await api(`/api/structures?${params}`);
      if (version !== requestVersion || currentView !== 'visualizer') return;
      result = data;
      render();
      $('#viz-content').hidden = false;
    } catch (error) {
      if (version !== requestVersion) return;
      $('#viz-error').textContent = `Could not load the visualizer: ${error.message}. Try Refresh data.`;
      $('#viz-error').hidden = false;
    } finally {
      if (version === requestVersion) $('#viz-content').setAttribute('aria-busy', 'false');
    }
  }

  function move(next) {
    pause();
    listMessage = '';
    step = Math.max(0, Math.min(limit(), next));
    render();
  }

  function play() {
    if (timer) return pause();
    if (!result) return;
    listMessage = '';
    if (step === limit()) step = 0;
    $('#viz-play').textContent = 'Ⅱ';
    $('#viz-play').setAttribute('aria-label', 'Pause traversal');
    $('#viz-play').title = 'Pause traversal';
    timer = setInterval(() => {
      step++;
      render();
      if (step >= limit()) pause();
    }, Number($('#viz-speed').value));
  }

  function listFields() {
    const operation = $('#viz-list-operation').value;
    const needsValue = ['append', 'insert', 'search'].includes(operation);
    const needsIndex = ['insert', 'remove'].includes(operation);
    const size = result ? result.practice_linked.length : 0;
    $('#viz-list-value').disabled = !needsValue;
    $('#viz-list-value').required = needsValue;
    $('#viz-list-index').disabled = !needsIndex;
    $('#viz-list-index').required = needsIndex;
    $('#viz-list-index').max = Math.max(0, size - (operation === 'remove' ? 1 : 0));
    $('#viz-list-run').disabled = !result || (operation === 'remove' && !size) || (['append', 'insert'].includes(operation) && size >= 250);
  }

  $('#viz-list-operation').addEventListener('change', listFields);
  $('#viz-list-actions').addEventListener('submit', event => {
    event.preventDefault();
    if (!result) return;
    action(async () => {
      pause();
      const version = requestVersion;
      const operation = $('#viz-list-operation').value;
      const data = await post('/api/list', { action: operation, value: $('#viz-list-value').value, index: Number($('#viz-list-index').value) });
      if (version !== requestVersion || !result) return;
      result.practice_linked = data.linked;
      step = operation === 'search' ? data.visited.length : 0;
      listMessage = operation === 'search' ? (data.found === null ? `Not found · ${data.visited.length} nodes checked` : `Found at index ${data.found} · ${data.visited.length} nodes checked`) : operation === 'remove' ? `Deleted: ${data.value} · ${data.linked.length} nodes` : `${operation[0].toUpperCase() + operation.slice(1)} complete · ${data.linked.length} nodes`;
      render();
    });
  });
  for (const [selector, operation] of [['#viz-enqueue', 'enqueue'], ['#viz-dequeue', 'process']]) {
    $(selector).addEventListener('click', () => action(async () => {
      const data = await post('/api/queue', { action: operation });
      applyState(data.state);
      processedJob = data.processed;
      notify(operation === 'enqueue' ? 'Meal snapshot enqueued at the rear.' : `Job #${data.processed.id} dequeued from the front.`);
    }));
  }
  ['#viz-topic', '#viz-order', '#viz-start'].forEach(selector => $(selector).addEventListener('change', load));
  $('#viz-refresh').addEventListener('click', () => action(async () => { applyState(await api('/api/state')); }));
  $('#viz-next').addEventListener('click', () => move(step + 1));
  $('#viz-prev').addEventListener('click', () => move(step - 1));
  $('#viz-reset').addEventListener('click', () => move(0));
  $('#viz-step').addEventListener('input', event => move(Number(event.target.value)));
  $('#viz-play').addEventListener('click', play);
  $('#viz-speed').addEventListener('change', () => { if (timer) { pause(); play(); } });
  $('#viz-push').addEventListener('click', () => action(() => editMeal({ action: 'add', food_id: $('#viz-food').value, grams: 100 }, 'Previous meal pushed. Food added to your current meal.')));
  $('#viz-pop').addEventListener('click', () => action(() => editMeal({ action: 'undo' }, 'Top state popped and restored as your meal.')));
  document.addEventListener('aminomatch-view', () => { pause(); ++requestVersion; if (currentView === 'visualizer' && state) load(); });
  document.addEventListener('aminomatch-state', () => { processedJob = null; if (currentView === 'visualizer') load(); });
  document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
  if (state && currentView === 'visualizer') load();
})();