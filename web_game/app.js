const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const state = {
  levels: [],
  level: null,
  backend: null,
  sessionId: null,
  x: 50,
  y: 24,
  selectedEdge: null,
  collecting: false,
  resultShown: false,
};
const costStatus = document.createElement("span");
costStatus.id = "cost-status";
costStatus.className = "cost-status";
costStatus.hidden = true;
$(".game-footer").append(costStatus);
const modalTripCost = document.createElement("p");
modalTripCost.id = "modal-trip-cost";
modalTripCost.className = "modal-trip-cost";
modalTripCost.hidden = true;
$("#floor-picker").before(modalTripCost);
document.body.insertAdjacentHTML("beforeend", `<div class="modal-backdrop" id="result-modal" hidden><div class="result-modal" role="dialog" aria-modal="true" aria-labelledby="result-title"><span class="eyebrow">RESULTADO DA FASE</span><h2 id="result-title"></h2><p id="result-summary"></p><div class="result-costs" id="result-costs" hidden><div><span>SEU GASTO</span><strong id="result-spent"></strong></div><div><span>MENOR CUSTO POSSÍVEL</span><strong id="result-optimal"></strong></div></div><div class="result-actions"><button type="button" class="primary-button" id="result-next">Próxima fase <span>↗</span></button><button type="button" class="secondary-button" id="result-retry">Repetir fase</button><button type="button" class="secondary-button" id="result-menu">Voltar ao menu principal</button></div></div></div>`);
const typeNames = {
  collect_and_exit: "Coleta e saída",
  hamilton: "Caminho Hamiltoniano",
  economic: "Menor custo",
  euler: "Trilha Euleriana",
  final: "Ida e volta",
};
const pad = (n) => String(n).padStart(2, "0");
const spriteDigits = (n) =>
  pad(n).split("").map((digit) =>
    `<img src="assets/digit-${digit}.svg" alt="" draggable="false">`,
  ).join("");
const itemSprite = (item) => {
  const name = `${item.id} ${item.name}`.toLowerCase();
  if (name.includes("chave")) return "key";
  if (name.includes("fus")) return "fuse";
  if (name.includes("cart")) return "card";
  if (name.includes("moeda")) return "coin";
  if (name.includes("radio") || name.includes("rádio")) return "radio";
  if (name.includes("reli")) return "relic";
  return "paper";
};
async function api(path, body) {
  const r = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json();
  if (!r.ok)
    throw new Error(data.error || "Erro de comunicação com o motor Python.");
  return data;
}
function showScreen(name) {
  if (name !== "game") $("#result-modal").hidden = true;
  $$(".screen").forEach((s) =>
    s.classList.toggle("active", s.id === `screen-${name}`),
  );
  $("#top-back").hidden = name === "menu";
  if (name === "select") renderPhaseGrid();
  if (name === "algorithms") renderAlgorithms();
  if (name === "menu") $("#top-back").hidden = true;
}
$$("[data-screen]").forEach((b) =>
  b.addEventListener("click", () => showScreen(b.dataset.screen)),
);
$("#top-back").onclick = () => showScreen("menu");
function renderPhaseGrid() {
  const grid = $("#phase-grid");
  grid.innerHTML = state.levels
    .map(
      (l) =>
        `<button class="phase-card" data-phase="${l.id}"><span class="phase-number">${pad(l.number)}</span><span><b>${l.name}</b><small>${l.vertices.length} andares · ${l.edges.length} elevadores</small><small class="phase-type">${typeNames[l.type] || l.type}</small></span><span class="phase-arrow">↗</span></button>`,
    )
    .join("");
  $$(".phase-card").forEach(
    (b) => (b.onclick = () => startGame(b.dataset.phase)),
  );
}
async function startGame(id) {
  try {
    const response = await api("/api/game/start", { level_id: id });
    state.sessionId = response.session_id;
    state.level = response.level;
    state.backend = response;
    state.x = 50;
    state.y = 24;
    state.selectedEdge = null;
    state.collecting = false;
    state.resultShown = false;
    $("#result-modal").hidden = true;
    $("#elevator-modal").hidden = true;
    (($("#game-phase").textContent =
      `MISSÃO ${pad(state.level.number)} / ${state.level.vertices.length} ANDARES`),
      ($("#game-title").textContent = state.level.name),
      ($("#game-description").textContent =
        `${typeNames[state.level.type] || state.level.type}. Conclua o desafio no motor Python.`),
      showScreen("game"),
      renderGame(),
      $("#game-frame").focus());
  } catch (error) {
    showToast(error.message);
  }
}
function incidentEdges() {
  return state.level.edges
    .map((edge, index) => ({ edge, index }))
    .filter(
      ({ edge }) =>
        edge[0] === state.backend.current_floor ||
        edge[1] === state.backend.current_floor,
    );
}
function renderElevators() {
  const layer = $("#elevator-layer");
  layer.innerHTML = "";
  const elevators = incidentEdges();
  elevators.forEach(({ edge, index }, position) => {
    const target = edge[0] === state.backend.current_floor ? edge[1] : edge[0];
    const allowed = state.backend.valid_destinations.includes(target);
    const cost = formatCost(edge[2]);
    const el = document.createElement("button");
    el.className = "elevator elevator-a";
    el.style.left = elevators.length === 1
      ? "calc((100% - var(--elevator-width)) / 2)"
      : `calc((100% - var(--elevator-width)) * ${position / (elevators.length - 1)})`;
    el.dataset.edge = index;
    el.disabled = !allowed;
    el.setAttribute("aria-label", `Elevador ${String.fromCharCode(65 + index)} para o andar ${pad(target)}, custo ${cost}${allowed ? "" : ", bloqueado"}`);
    el.innerHTML = `<span class="elevator-sign"><span>ELEVADOR ${String.fromCharCode(65 + index)}</span><span class="elevator-digits">${spriteDigits(target)}</span></span>${isCostLevel() ? `<span class="elevator-cost">CUSTO ${cost}</span>` : ""}`;
    el.onclick = () => openElevator(index, edge, allowed);
    layer.append(el);
  });
}
function renderItems() {
  const layer = $("#item-layer");
  layer.innerHTML = "";
  (state.backend.items_here || []).forEach((item, i) => {
    const el = document.createElement("button");
    el.className = "item-pixel";
    el.style.left = `${25 + i * 16}%`;
    el.dataset.itemId = item.id;
    el.setAttribute("aria-label", `Coletar ${item.name}`);
    el.innerHTML = `<img src="assets/item-${itemSprite(item)}.svg" alt="" draggable="false"><small>${item.name}</small>`;
    el.onclick = () => collectHere(item.id);
    layer.append(el);
  });
}
async function collectHere(itemId) {
  if (state.collecting || !state.backend.items_here?.some((item) => item.id === itemId)) return;
  state.collecting = true;
  try {
    state.backend = await api("/api/game/collect", {
      session_id: state.sessionId,
      item_id: itemId,
    });
    showToast(state.backend.message);
  } catch (error) {
    showToast(error.message);
  } finally {
    state.collecting = false;
    renderGame();
  }
}
function overlapsHorizontally(character, object) {
  return character.right - 8 >= object.left + 6 &&
    character.left + 8 <= object.right - 6;
}
function nearbyElevator() {
  const character = $("#character").getBoundingClientRect();
  const center = (character.left + character.right) / 2;
  return $$("#elevator-layer .elevator")
    .filter((el) => overlapsHorizontally(character, el.getBoundingClientRect()))
    .map((el) => {
      const edgeData = incidentEdges().find(({ index }) => index === Number(el.dataset.edge));
      const rect = el.getBoundingClientRect();
      return { el, edgeData, distance: Math.abs(center - (rect.left + rect.right) / 2) };
    })
    .sort((a, b) => a.distance - b.distance)[0];
}
function checkItemCollision() {
  if (state.collecting || !state.backend.items_here?.length) return;
  const character = $("#character").getBoundingClientRect();
  const item = $$("#item-layer .item-pixel").find((el) => {
    const rect = el.getBoundingClientRect();
    return overlapsHorizontally(character, rect) &&
      character.bottom >= rect.top && character.top <= rect.bottom;
  });
  if (item) collectHere(item.dataset.itemId);
}
function updateElevatorHint() {
  const near = nearbyElevator();
  $$("#elevator-layer .elevator").forEach((el) =>
    el.classList.toggle("nearby", el === near?.el),
  );
  const hint = $("#interaction-hint");
  hint.classList.toggle("visible", Boolean(near));
  if (near) {
    const { edge, index } = near.edgeData;
    const target = edge[0] === state.backend.current_floor ? edge[1] : edge[0];
    hint.querySelector("span").textContent = `Elevador ${String.fromCharCode(65 + index)} · andar ${pad(target)}${isCostLevel() ? ` · custo ${formatCost(edge[2])}` : ""}${near.el.disabled ? " bloqueado" : ""}`;
  }
}
function renderMap() {
  const map = $("#building-map");
  map.innerHTML = "";
  state.level.vertices
    .slice()
    .reverse()
    .forEach((f) => {
      const connectedTo = state.level.edges.filter((e) => e.includes(f)).length;
      const row = document.createElement("div");
      row.className = `map-floor ${f === state.backend.current_floor ? "current" : ""} ${state.backend.visited_floors.includes(f) ? "visited" : ""}`;
      row.innerHTML = `<span>${pad(f)}</span><span class="line"></span><i></i><span class="elev">${connectedTo}▣</span>`;
      map.append(row);
    });
}
function renderObjectives() {
  const required = state.level.items.filter((item) => item.kind !== "bonus");
  const collected = state.backend.collected || [];
  const done = required.filter((item) => collected.includes(item.id)).length;
  $("#objective-list").innerHTML =
    `<div class="objective complete"><span class="check">✓</span><div><strong>Explorar o andar ${pad(state.backend.current_floor)}</strong><small>${state.backend.visited_floors.length} andar(es) visitado(s)</small></div></div>${required.length ? `<div class="objective ${done === required.length ? "complete" : ""}"><span class="check">${done === required.length ? "✓" : "02"}</span><div><strong>Itens essenciais</strong><small>${done} / ${required.length} coletado(s)</small></div></div>` : ""}<div class="objective ${state.backend.is_complete ? "complete" : ""}"><span class="check">${state.backend.is_complete ? "✓" : "03"}</span><div><strong>${typeNames[state.level.type] || "Concluir desafio"}</strong><small>Saída: andar ${pad(state.level.exit)}</small></div></div>`;
  const progress = Math.round(
    (state.backend.visited_floors.length / state.level.vertices.length) * 100,
  );
  $("#progress-bar").style.width = `${Math.max(15, progress)}%`;
  $("#game-status").textContent = state.backend.is_complete
    ? "CONCLUÍDA"
    : state.backend.is_finished
      ? "ROTA FINALIZADA"
    : state.backend.is_blocked
      ? "BLOQUEADA"
      : "EM ANDAMENTO";
}
function renderGame() {
  const floor = state.backend.current_floor;
  $("#floor-label").innerHTML = spriteDigits(floor);
  $("#floor-label").setAttribute("aria-label", `Andar ${pad(floor)}`);
  $("#wall-number").innerHTML = spriteDigits(floor);
  $("#wall-number").setAttribute("aria-label", `Andar ${pad(floor)}`);
  $("#character").style.left = `${state.x}%`;
  $("#character").style.bottom = `${state.y}%`;
  renderElevators();
  renderItems();
  renderMap();
  renderObjectives();
  $("#coordinate").textContent =
    `X ${state.x.toFixed(1)}  Y ${state.y.toFixed(1)}`;
  $("#log-line").textContent =
    state.backend.message || `Você está no andar ${pad(floor)}.`;
  const costStatus = $("#cost-status");
  costStatus.hidden = !isCostLevel();
  if (isCostLevel()) costStatus.textContent = `CUSTO ACUMULADO: ${formatCost(state.backend.total_cost ?? 0)}`;
  updateElevatorHint();
  checkItemCollision();
  showResultIfFinished();
}
function openElevator(index, edge, allowed) {
  if (!allowed) {
    showToast("Esse destino está bloqueado pelo desafio atual.");
    return;
  }
  state.selectedEdge = { index, edge };
  const target = edge[0] === state.backend.current_floor ? edge[1] : edge[0];
  $("#modal-elevator-name").textContent = String.fromCharCode(65 + index);
  $("#floor-picker").innerHTML =
    `<button class="floor-option selected">${pad(target)}</button>`;
  $("#modal-trip-cost").hidden = !isCostLevel();
  $("#modal-trip-cost").textContent = isCostLevel()
    ? `Custo deste elevador: ${formatCost(edge[2])}. Total após a viagem: ${formatCost((state.backend.total_cost ?? 0) + edge[2])}.`
    : "";
  $("#travel-button").dataset.floor = target;
  $("#elevator-modal").hidden = false;
}
async function travel() {
  const target = Number($("#travel-button").dataset.floor);
  try {
    state.backend = await api("/api/game/move", {
      session_id: state.sessionId,
      destination: target,
    });
    $("#elevator-modal").hidden = true;
    showToast(state.backend.message);
    renderGame();
  } catch (error) {
    showToast(error.message);
  }
}
function move(dx) {
  state.x = Math.max(7, Math.min(93, state.x + dx));
  const character = $("#character");
  character.classList.toggle("facing-left", dx < 0);
  character.classList.add("walking");
  clearTimeout(move.stopTimer);
  move.stopTimer = setTimeout(() => character.classList.remove("walking"), 180);
  renderGame();
}
function showToast(t) {
  $("#toast").textContent = t;
  $("#toast").classList.add("show");
  setTimeout(() => $("#toast").classList.remove("show"), 2400);
}
function useElevator() {
  const near = nearbyElevator();
  if (near) openElevator(near.edgeData.index, near.edgeData.edge, !near.el.disabled);
  else showToast("Aproxime-se de um elevador para usá-lo.");
}
function isCostLevel() {
  return state.level?.type === "economic" || state.level?.type === "final";
}
function formatCost(value) {
  return Number(value).toLocaleString("pt-BR", { maximumFractionDigits: 2 });
}
function showResultIfFinished() {
  if (state.resultShown || !(state.backend.is_finished || state.backend.is_complete)) return;
  state.resultShown = true;
  const optimal = state.backend.is_complete;
  $("#result-title").textContent = optimal ? "Fase concluída!" : "Rota concluída";
  $("#result-summary").textContent = isCostLevel()
    ? optimal
      ? "Você encontrou o caminho de menor custo."
      : "Você chegou ao fim, mas esse gasto não é o menor possível."
    : state.backend.message || "Desafio concluído.";
  $("#result-costs").hidden = !isCostLevel();
  if (isCostLevel()) {
    $("#result-spent").textContent = formatCost(state.backend.total_cost);
    $("#result-optimal").textContent = formatCost(state.backend.optimal_cost);
  }
  const index = state.levels.findIndex((level) => level.id === state.level.id);
  const nextLevel = state.levels[index + 1];
  $("#result-next").hidden = !nextLevel;
  $("#result-next").dataset.phase = nextLevel?.id || "";
  $("#result-modal").hidden = false;
  $("#result-retry").focus();
}
const touchControls = document.createElement("div");
touchControls.className = "touch-controls";
touchControls.setAttribute("aria-label", "Controles do jogo");
touchControls.innerHTML = `<div class="touch-directions"><button type="button" data-move="-4" aria-label="Mover para a esquerda">◀</button><button type="button" data-move="4" aria-label="Mover para a direita">▶</button></div><button type="button" data-action="elevator">Elevador</button><button type="button" data-action="reset">Reiniciar</button>`;
$(".game-column").insertBefore(touchControls, $("#game-frame"));
touchControls.querySelectorAll("[data-move]").forEach((button) => {
  let repeat;
  const stop = () => clearInterval(repeat);
  button.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    button.setPointerCapture(event.pointerId);
    move(Number(button.dataset.move));
    repeat = setInterval(() => move(Number(button.dataset.move)), 100);
  });
  button.addEventListener("pointerup", stop);
  button.addEventListener("pointercancel", stop);
  button.addEventListener("lostpointercapture", stop);
});
touchControls.querySelector('[data-action="elevator"]').onclick = useElevator;
touchControls.querySelector('[data-action="reset"]').onclick = resetGame;
$("#game-frame").addEventListener("click", () => $("#game-frame").focus());
window.addEventListener("keydown", (e) => {
  if (!state.level || !$("#screen-game").classList.contains("active")) return;
  if (!$("#result-modal").hidden) return;
  if (!$("#elevator-modal").hidden) return;
  const k = e.key.toLowerCase();
  if (["a", "d", "e", "r", "arrowleft", "arrowright"].includes(k))
    e.preventDefault();
  if (k === "a" || k === "arrowleft") move(-4);
  if (k === "d" || k === "arrowright") move(4);
  if (k === "e") useElevator();
  if (k === "r") resetGame();
});
$("#modal-close").onclick = () => ($("#elevator-modal").hidden = true);
$("#travel-button").onclick = travel;
async function resetGame() {
  try {
    state.backend = await api("/api/game/reset", {
      session_id: state.sessionId,
    });
    state.x = 50;
    state.y = 24;
    state.resultShown = false;
    $("#result-modal").hidden = true;
    showToast(state.backend.message);
    renderGame();
  } catch (error) {
    showToast(error.message);
  }
}
$("#result-menu").onclick = () => showScreen("menu");
$("#result-retry").onclick = resetGame;
$("#result-next").onclick = () => startGame($("#result-next").dataset.phase);
function renderAlgorithms() {
  const select = $("#algorithm-phase");
  select.innerHTML = state.levels
    .map(
      (l) =>
        `<option value="${l.id}">Fase ${pad(l.number)} — ${l.name}</option>`,
    )
    .join("");
  $("#algorithm-list").innerHTML = [
    ["connect", "Conectividade"],
    ["shortest", "Dijkstra / menor custo"],
    ["hamilton", "Hamiltoniano"],
    ["euler", "Euleriano"],
  ]
    .map(
      ([id, n]) =>
        `<button class="algorithm-button" data-algo="${id}">${n}<span>Executar ↗</span></button>`,
    )
    .join("");
  $$(".algorithm-button").forEach(
    (b) => (b.onclick = () => runAlgorithm(b.dataset.algo, select.value)),
  );
}
async function runAlgorithm(algorithm, levelId) {
  try {
    const r = await api("/api/algorithm", { algorithm, level_id: levelId });
    $("#algorithm-output").textContent =
      `${r.algorithm}\n\n${r.ok ? "PASSOU" : "FALHOU"}\n${typeof r.details === "object" ? JSON.stringify(r.details, null, 2) : r.details || ""}`;
  } catch (error) {
    $("#algorithm-output").textContent = error.message;
  }
}
function editorConfig() {
  const vertices = Array.from(
    { length: Number($("#editor-vertices").value) },
    (_, i) => i + 1,
  );
  const edges = $("#editor-edges")
    .value.split(/\n/)
    .map((x) => x.replace(/^\+/, "").split(",").map(Number))
    .filter((x) => x.length >= 2 && !x.some(Number.isNaN))
    .map((x) => (x.length > 2 ? x : [x[0], x[1], 1]));
  const type = $("#editor-challenge").value;
  const challenge = { type };
  if (type === "hamilton")
    challenge.end_floor = Number($("#editor-exit").value);
  if (type === "economic" || type === "final")
    challenge.destination_floor = Number($("#editor-exit").value);
  if (type === "final")
    challenge.return_floor = Number($("#editor-start").value);
  if (type === "euler") challenge.reference_trail = [];
  return {
    id: `custom-${Date.now()}`,
    number: 99,
    name: $("#editor-name").value,
    graph: { vertices, edges },
    start_floor: Number($("#editor-start").value),
    exit_floor: Number($("#editor-exit").value),
    items: [],
    exit_requirements: { keys: [], challenges: [] },
    challenge,
    optional_objectives: [],
    rewards: { completion: 300 },
  };
}
async function validateEditor() {
  try {
    const result = await api("/api/level/validate", { config: editorConfig() });
    $("#editor-result").className = "validation-result success";
    $("#editor-result").textContent =
      `✓ ${result.message} ${result.level.edges.length} elevador(es) serão criados.`;
  } catch (error) {
    $("#editor-result").className = "validation-result error";
    $("#editor-result").textContent = `✕ ${error.message}`;
  }
}
$("#validate-level").onclick = validateEditor;
$("#save-level").onclick = async () => {
  try {
    const result = await api("/api/level/save", { config: editorConfig() });
    state.levels.push(result.level);
    showToast(result.message);
  } catch (error) {
    showToast(error.message);
  }
};
function menuArt() {
  const b = $("#menu-building");
  b.innerHTML = Array.from(
    { length: 13 },
    (_, i) => `<span><i></i><i></i><i></i><b>${pad(13 - i)}</b></span>`,
  ).join("");
}
async function boot() {
  menuArt();
  try {
    const health = await api("/api/health");
    const data = await api("/api/levels");
    state.levels = data.levels;
    $("#header-status").textContent =
      `MOTOR PYTHON ONLINE · ${health.levels} FASES`;
    showScreen("menu");
  } catch (error) {
    $("#header-status").textContent = "MOTOR PYTHON OFFLINE";
    $("#log-line").textContent =
      "Execute server.py para conectar o frontend ao motor Python.";
    showScreen("menu");
  }
}
$("#continue-button").onclick = () => {
  if (state.levels.length) startGame(state.levels[0].id);
  else showToast("Motor Python offline.");
};
boot();
