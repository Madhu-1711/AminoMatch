"use strict";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const escapeHTML = (value) => String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const format = (number, digits = 1) => Number(number).toLocaleString(undefined, { maximumFractionDigits: digits });
const icons = { Legumes: "◒", Grains: "❧", Soy: "▧", "Nuts & seeds": "✳", "Eggs & dairy": "◐", "Meat & fish": "≋" };
const titles = { builder: "Meal builder", library: "Food library", phase1: "Meal tools", phase2: "Discover pairings", roadmap: "Getting started", method: "How the scores work", visualizer: "Structure visualizer", phase3: "Phase 3 analysis" };
let state = null;
let currentView = "builder";
let busy = false;
let toastTimer;
let labRequest = 0;

function notify(message, isError = false) {
  clearTimeout(toastTimer);
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.hidden = false;
  toastTimer = setTimeout(() => { toast.hidden = true; }, isError ? 8000 : 4000);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Something went wrong. Please try again.");
  return data;
}

const post = (path, data) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });

async function action(work) {
  if (busy) return;
  busy = true;
  document.body.setAttribute("aria-busy", "true");
  try { await work(); }
  catch (error) { notify(error.message || "Could not connect to the server.", true); }
  finally { busy = false; document.body.removeAttribute("aria-busy"); }
}

function populateSelect(selector, options, placeholder = null) {
  const element = $(selector);
  const previous = element.value;
  element.innerHTML = (placeholder === null ? "" : `<option value="">${escapeHTML(placeholder)}</option>`)
    + options.map(([value, label]) => `<option value="${escapeHTML(value)}">${escapeHTML(label)}</option>`).join("");
  if (options.some(([value]) => value === previous)) element.value = previous;
}

function applyState(next) {
  ++labRequest;
  state = next;
  const options = state.foods.map((food) => [food.id, food.name]);
  populateSelect("#food-select", options, "Select a food…");
  populateSelect("#graph-start", options);
  const categories = [...new Set(state.foods.map((food) => food.category))].sort();
  populateSelect("#category-filter", categories.map((item) => [item, item]), "All categories");
  $("#food-names").innerHTML = state.foods.map((food) => `<option value="${escapeHTML(food.name)}"></option>`).join("");
  $("#food-count").textContent = state.foods.length;
  $("#dataset-source").textContent = state.source;
  $("#try-pair").disabled = !["lentils", "brown-rice"].every((id) => state.foods.some((food) => food.id === id));
  renderMeal();
  renderProfile();
  renderLibrary();
  renderStackQueue();
  $("#reference-table").innerHTML = state.analysis.groups.map((group) => `<tr><td>${escapeHTML(group.name)}</td><td>${group.reference_mg_per_g}</td></tr>`).join("");
  document.dispatchEvent(new Event('aminomatch-state'));
}

function renderMeal() {
  const meal = state.meal;
  $("#portion-count").textContent = `${meal.length} portion${meal.length === 1 ? "" : "s"}`;
  $("#meal-list").innerHTML = meal.length ? meal.map((portion, index) => {
    const food = state.foods.find((item) => item.id === portion.food_id);
    return `<div class="meal-row"><span class="food-avatar" aria-hidden="true">${icons[food.category] || "❧"}</span><div class="meal-row-info"><strong>${escapeHTML(food.name)}</strong><small>${format(portion.grams)} g serving · ${escapeHTML(food.category)}</small></div><span class="meal-row-protein">${format(food.protein_g * portion.grams / 100)} g protein</span><button class="icon-button" data-remove="${index}" aria-label="Remove ${escapeHTML(food.name)}">×</button></div>`;
  }).join("") : '<div class="empty-state"><span>◌</span><strong>A good meal starts with one food.</strong><p>Add your first ingredient to see its amino acid profile.</p></div>';
  $("#total-protein").innerHTML = `${format(state.analysis.protein_g)} <small>g</small>`;
  $("#total-eaa").innerHTML = `${format(state.analysis.essential_mg, 0)} <small>mg</small>`;
  $("#undo").disabled = $("#lab-undo").disabled = !state.undo_count;
  $("#clear").disabled = $("#queue-meal").disabled = $("#lab-enqueue").disabled = !meal.length;
}

function renderProfile() {
  const a = state.analysis;
  const present = state.meal.length > 0;
  $("#score").innerHTML = `${present ? format(a.score, 0) + '%' : '—'}<small>pattern score</small>`;
  $(".score-ring").style.setProperty("--score", Math.min(100, a.score));
  $("#profile-title").textContent = !present ? "Let’s see your profile" : a.meets_pattern ? "Meets the reference pattern" : "There’s room to complement";
  $("#profile-subtitle").textContent = !present ? "Add a food to begin exploring." : `${a.met_count} of 9 groups meet the adult pattern.${a.meets_pattern ? " Not adjusted for digestibility." : " Try a different mix of foods."}`;
  $("#amino-bars").innerHTML = a.groups.map((group) => `<div class="amino-row ${present && !group.meets ? 'low' : ''}"><span class="amino-name">${escapeHTML(group.name)}</span><div class="bar-track" role="meter" aria-label="${escapeHTML(group.name)} reference coverage" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.min(100, group.coverage)}" aria-valuetext="${group.coverage}% of reference, ${group.amount_mg} mg"><div class="bar-fill" style="width:${Math.min(100, group.coverage)}%"></div></div><span class="amino-percent">${present ? format(group.coverage, 0) + '%' : '—'}</span></div>`).join("");
  $("#insight-title").textContent = !present ? "Aim for balance, not just a bigger number." : `Lowest-coverage group: ${a.limiting}.`;
  $("#insight-text").textContent = !present ? "A limiting amino acid is the group with the lowest coverage relative to the reference pattern." : a.meets_pattern ? "Every group meets this reference pattern. Increasing the portion changes the amounts, not the profile’s proportions." : `This group reaches ${format(a.score)}% of the pattern. Explore foods with a higher proportion of this group—not just a larger serving of the same food.`;
}

function renderLibrary() {
  if (!state) return;
  const query = $("#library-search").value.trim().toLowerCase();
  const category = $("#category-filter").value;
  const foods = state.foods.filter((food) => (!category || food.category === category) && `${food.name} ${food.category}`.toLowerCase().includes(query));
  $("#library-count").textContent = `${foods.length} food${foods.length === 1 ? '' : 's'}`;
  $("#food-grid").innerHTML = foods.length ? foods.map((food) => `<article class="food-card"><div class="food-card-top"><span class="food-avatar" aria-hidden="true">${icons[food.category] || "❧"}</span><span class="tag">${escapeHTML(food.category)}</span></div><h3>${escapeHTML(food.name)}</h3><p>Per 100 g · ${food.profile.met_count}/9 reference groups met</p><div class="food-card-metrics"><div><strong>${format(food.protein_g)}<span> g</span></strong><span>Protein</span></div><div><strong>${format(food.profile.score, 0)}<span> %</span></strong><span>Pattern score</span></div></div><div class="food-card-actions"><button class="text-button" data-detail="${escapeHTML(food.id)}">Amino profile ↗</button><button class="button secondary" data-add="${escapeHTML(food.id)}">+ Add 100 g</button></div></article>`).join("") : '<div class="empty-state"><strong>No foods match your search.</strong><p>Try a different name or category.</p></div>';
}

function renderStackQueue() {
  const count = state.undo_count;
  $("#saved-count").textContent = state.queue.length;
  $("#stack-visual").innerHTML = count ? Array.from({ length: Math.min(count, 4) }, (_, i) => `<div class="stack-level">${i === 0 ? 'TOP → ' : ''}Saved meal state ${count - i}</div>`).join("") + `<p class="small-note">${count} saved state${count === 1 ? '' : 's'}${count > 4 ? ' · showing top 4' : ''}</p>` : '<p class="small-note">Stack is empty. Edit your meal to push its previous state.</p>';
  $("#queue-visual").innerHTML = state.queue.length ? state.queue.map((job, i) => `<span class="queue-node">${i === 0 ? 'FRONT → ' : ''}Job #${job.id}<small>${job.portions} portions</small></span>`).join("") : '<p class="small-note">Queue is empty. Add a meal snapshot to begin.</p>';
  $("#process-queue").disabled = state.queue.length === 0;
}

function showFood(id) {
  const food = state.foods.find((item) => item.id === id);
  if (!food) return;
  const amino = Object.entries(food.profile.amino_mg);
  $("#food-detail").innerHTML = `<h2>${escapeHTML(food.name)}</h2><p>${escapeHTML(food.category)} · ${escapeHTML(state.source)} · per 100 g</p><div class="detail-summary"><span><strong>${format(food.protein_g)} g</strong>Protein</span><span><strong>${format(food.profile.essential_mg, 0)} mg</strong>9 essential amino acids</span></div><div class="table-wrap"><table><thead><tr><th>Amino acid</th><th>Amount (mg)</th></tr></thead><tbody>${amino.map(([key, amount]) => `<tr><td>${escapeHTML(key[0].toUpperCase() + key.slice(1))}${['cysteine', 'tyrosine'].includes(key) ? ' (supporting group)' : ''}</td><td>${format(amount, 2)}</td></tr>`).join("")}</tbody></table></div><p class="small-note">Cysteine and tyrosine support the combined scoring groups but are excluded from the nine-essential-amino-acid total. Zero is a reported value, not a missing value.</p>`;
  $("#food-dialog").showModal();
}

function treeHTML(node, side = "root") {
  if (!node) return '';
  const children = treeHTML(node.left, "left") + treeHTML(node.right, "right");
  return `<li><span class="tree-label"><small>${side}</small>${escapeHTML(node.name)}</span>${children ? `<ul>${children}</ul>` : ''}</li>`;
}

async function loadLabs(target = null) {
  if (!state) return;
  const requestId = ++labRequest;
  const params = new URLSearchParams({ order: $("#traversal-order").value, start: $("#graph-start").value });
  if (target) params.set("target", target);
  const data = await api(`/api/structures?${params}`);
  if (requestId !== labRequest) return;
  $("#linked-visual").innerHTML = data.linked.map((name, i) => `<div class="list-node"><span><small>${i === 0 ? 'HEAD · ' : ''}NODE ${i + 1}${i === data.linked.length - 1 ? ' · TAIL' : ''}</small>${escapeHTML(name)}</span><b>→</b></div>`).join("") + '<span class="small-note">None</span>';
  const e = data.efficiency;
  $("#efficiency").innerHTML = `<div class="efficiency-item"><h3>Iterative · a for loop</h3><strong>${format(e.iterative_sum)} g</strong><p>${e.additions} additions · ${e.time} time · ${e.iterative_space} auxiliary space</p></div><div class="efficiency-item"><h3>Recursive · a function calling itself</h3><strong>${format(e.recursive_sum)} g</strong><p>${e.recursive_calls} calls (including base case) · ${e.additions} additions · ${e.recursive_space} space</p></div>`;
  if ($("#tree-visual")) $("#tree-visual").innerHTML = `<ul>${treeHTML(data.tree)}</ul>`;
  $("#traversal-result").innerHTML = data.traversal.map((name) => `<span>${escapeHTML(name)}</span>`).join("");
  const names = Object.fromEntries(state.foods.map((food) => [food.id, food.name]));
  $("#graph-visual").innerHTML = Object.entries(data.graph).map(([id, neighbors]) => `<div class="adj-row"><strong>${escapeHTML(names[id])} →</strong><span>${neighbors.length ? neighbors.map((neighbor) => escapeHTML(names[neighbor])).join(' · ') : 'No edges — isolated node'}</span></div>`).join("");
  $("#bfs-result").innerHTML = data.bfs.order.map((id) => `<span>${escapeHTML(names[id])}</span>`).join("");
  if (target) {
    const search = data.search;
    $("#binary-result").innerHTML = `<div class="result-box"><strong>${search.found ? 'Found: ' + escapeHTML(search.found.name) : 'No exact match found.'}</strong> · ${search.steps.length} comparison${search.steps.length === 1 ? '' : 's'}</div><div class="table-wrap"><table><thead><tr><th>Step</th><th>Low</th><th>Mid</th><th>High</th><th>Compared with</th></tr></thead><tbody>${search.steps.map((step, i) => `<tr><td>${i + 1}</td><td>${step.low}</td><td>${step.mid}</td><td>${step.high}</td><td>${escapeHTML(step.name)}</td></tr>`).join('')}</tbody></table></div>`;
  }
}

function showView(view, updateHash = true) {
  if (!titles[view]) view = 'builder';
  currentView = view;
  $$('.view').forEach((section) => { section.hidden = section.id !== `view-${view}`; });
  $$('.nav-item').forEach((button) => { const active = button.dataset.view === view; button.classList.toggle('active', active); if (active) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current'); });
  $('#page-crumb').textContent = titles[view];
  document.title = `${titles[view]} · AminoMatch`;
  if (updateHash && location.hash !== `#${view}`) history.pushState(null, '', `#${view}`);
  if (['phase1', 'phase2'].includes(view)) loadLabs().catch((error) => notify(error.message, true));
  document.dispatchEvent(new Event('aminomatch-view'));
  window.scrollTo({ top: 0, behavior: 'instant' });
}

async function editMeal(data, message) {
  applyState(await post('/api/meal', data));
  if (message) notify(message);
}

async function enqueue() {
  const data = await post('/api/queue', { action: 'enqueue' });
  applyState(data.state);
  notify('Meal snapshot queued. Process it in Phase 1.');
}

function confirmReplacement() {
  const dialog = $('#confirm-dialog');
  return new Promise((resolve) => {
    dialog.returnValue = 'cancel';
    dialog.addEventListener('close', () => resolve(dialog.returnValue === 'replace'), { once: true });
    dialog.showModal();
  });
}

async function replaceDataset(work) {
  if (!await confirmReplacement()) return;
  applyState(await work());
  $('#queue-result').hidden = true;
  $('#binary-result').innerHTML = '';
  $('#csv-file').value = '';
  notify('Dataset loaded into the linked list. Meal, stack and queue reset.');
}

document.addEventListener('click', (event) => {
  const navigation = event.target.closest('[data-view]');
  if (navigation) showView(navigation.dataset.view);
  const remove = event.target.closest('[data-remove]');
  if (remove) action(() => editMeal({ action: 'remove', index: Number(remove.dataset.remove) }, 'Food removed. You can undo this change.'));
  const add = event.target.closest('[data-add]');
  if (add) action(() => editMeal({ action: 'add', food_id: add.dataset.add, grams: 100 }, '100 g added to your meal.'));
  const detail = event.target.closest('[data-detail]');
  if (detail) showFood(detail.dataset.detail);
});

$('#meal-form').addEventListener('submit', (event) => {
  event.preventDefault();
  action(() => editMeal({ action: 'add', food_id: $('#food-select').value, grams: Number($('#grams').value) }, 'Food added. Your amino acid profile is updated.'));
});
$('#try-pair').addEventListener('click', () => action(() => editMeal({ action: 'example' }, 'Example meal loaded: 100 g lentils + 100 g brown rice. Undo restores your previous meal.')));
['#undo', '#lab-undo'].forEach((selector) => $(selector).addEventListener('click', () => action(() => editMeal({ action: 'undo' }, 'Previous meal restored from the stack.'))));
$('#clear').addEventListener('click', () => action(() => editMeal({ action: 'clear' }, 'Meal cleared. Undo is available.')));
['#queue-meal', '#lab-enqueue'].forEach((selector) => $(selector).addEventListener('click', () => action(enqueue)));
$('#process-queue').addEventListener('click', () => action(async () => {
  const data = await post('/api/queue', { action: 'process' });
  applyState(data.state);
  const job = data.processed;
  $('#queue-result').hidden = false;
  $('#queue-result').innerHTML = `<strong>Processed job #${job.id}</strong><br>${format(job.analysis.protein_g)} g protein · ${format(job.analysis.essential_mg, 0)} mg essential amino acids · ${format(job.analysis.score)}% pattern score · ${job.analysis.met_count}/9 groups met.`;
  notify(`Job #${job.id} dequeued and analyzed.`);
}));
$('#expression-form').addEventListener('submit', (event) => {
  event.preventDefault();
  action(async () => {
    $('#expression-result').innerHTML = '';
    const data = await post('/api/expression', { expression: $('#expression').value });
    $('#expression-result').innerHTML = `<div class="result-box"><strong>Postfix:</strong> ${escapeHTML(data.postfix)}<br><strong>Result:</strong> ${format(data.result, 6)}</div><div class="table-wrap"><table><thead><tr><th>Token</th><th>Operator stack top</th><th>Output so far</th></tr></thead><tbody>${data.trace.map((step) => `<tr><td>${escapeHTML(step.token)}</td><td>${escapeHTML(step.operator_top)}</td><td>${escapeHTML(step.output) || '—'}</td></tr>`).join('')}</tbody></table></div><p class="small-note">Any remaining operators are popped after the final token to produce the postfix expression above.</p>`;
  });
});
$('#binary-form').addEventListener('submit', (event) => { event.preventDefault(); action(() => loadLabs($('#binary-target').value)); });
['#traversal-order', '#graph-start'].forEach((selector) => $(selector).addEventListener('change', () => { loadLabs().catch((error) => notify(error.message, true)); }));
$('#library-search').addEventListener('input', renderLibrary);
$('#category-filter').addEventListener('change', renderLibrary);
$('#close-dialog').addEventListener('click', () => $('#food-dialog').close());
$('#confirm-replace').addEventListener('click', () => $('#confirm-dialog').close('replace'));
$('#cancel-replace').addEventListener('click', () => $('#confirm-dialog').close('cancel'));
$('#import-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const file = $('#csv-file').files[0];
  if (!file) return;
  if (file.size > 1024 * 1024) return notify('Choose a CSV smaller than 1 MB.', true);
  const form = new FormData();
  form.append('file', file);
  action(() => replaceDataset(() => api('/api/dataset', { method: 'POST', body: form })));
});
$('#reset-dataset').addEventListener('click', () => action(() => replaceDataset(() => post('/api/dataset', { action: 'reset' }))));
window.addEventListener('popstate', () => showView(location.hash.slice(1), false));
window.addEventListener('hashchange', () => { if (location.hash.slice(1) !== currentView) showView(location.hash.slice(1), false); });

async function boot() {
  try {
    applyState(await api('/api/state'));
    $('#connection-error').hidden = true;
    showView(location.hash.slice(1) || 'builder', false);
  } catch (error) {
    $('#connection-error').hidden = false;
    notify(error.message || 'The server is unavailable.', true);
  }
}
$('#retry').addEventListener('click', boot);
boot();