(() => {
  "use strict";
  const $ = (selector) => document.querySelector(selector);
  const form = $("#search-form");
  const resultList = $("#result-list");
  const submit = $("#submit-button");
  const storageKey = "eventmatch_api_url_v2";
  const defaultUrl = location.protocol === "file:" ? "http://127.0.0.1:8000" : (location.pathname.startsWith("/app") ? location.origin : "http://127.0.0.1:8000");
  const storedUrl = (() => { try { return localStorage.getItem(storageKey); } catch (_) { return null; } })();
  let apiUrl = new URLSearchParams(location.search).get("api") || storedUrl || defaultUrl;
  let lastPayload = null;
  let previousSearch = null;
  let controller = null;
  let sequence = 0;
  let hasResult = false;
  let loading = false;

  const reasonLabels = {busy: "Занят на дату", over_budget: "Цена выше бюджета", wrong_format: "Не берёт этот формат", wrong_language: "Нет нужного языка", duration_too_long: "Мало часов", wrong_city: "Другой город", wrong_category: "Другая категория"};
  const states = ["initial", "loading", "success", "empty", "error"];
  const fieldIds = {event_format: "event-format", city: "city", date: "date", category: "category", budget: "budget", duration: "duration", language: "language", preferences: "preferences"};
  const demos = [
    {label: "01 · Спокойный ведущий", data: {city:"Алматы",date:"2026-10-15",event_format:"корпоратив",category:"Ведущий",budget:2000000,language:"русский",duration:6,preferences:"Спокойная ненавязчивая подача, интеллигентный юмор и уютная атмосфера"}},
    {label: "02 · Другая дата", data: {city:"Алматы",date:"2026-10-16",event_format:"корпоратив",category:"Ведущий",budget:2000000,language:"русский",duration:6,preferences:"Спокойная ненавязчивая подача, интеллигентный юмор и уютная атмосфера"}},
    {label: "03 · Редкая категория", data: {city:"Алматы",date:"2026-10-15",event_format:"свадьба",category:"Флорист",budget:600000,language:"русский",preferences:"Цветочные композиции под цветовую палитру свадьбы"}},
    {label: "04 · Нет совпадений", data: {city:"Алматы",date:"2026-12-31",event_format:"свадьба",category:"Флорист",budget:100000,language:"русский",preferences:"Цветочное оформление свадьбы"}},
    {label: "05 · Нет категории", data: {city:"Зарубежье",date:"2026-10-15",event_format:"свадьба",category:"Флорист",budget:600000,language:"русский",preferences:"Авторские цветочные композиции"}}
  ];

  function node(tag, className = "", text = "") {
    const el = document.createElement(tag);
    el.className = className;
    if (text !== null) el.textContent = String(text);
    return el;
  }
  const money = (value) => `${new Intl.NumberFormat("ru-RU").format(value)} ₸`;
  const dateText = (value) => new Intl.DateTimeFormat("ru-RU", {day:"numeric",month:"long",year:"numeric"}).format(new Date(`${value}T12:00:00`));

  function setState(name) {
    states.forEach((s) => { $(`#${s}-state`).hidden = s !== name; });
    $(".results-card").setAttribute("aria-busy", String(name === "loading"));
    $("#result-count").hidden = name !== "success";
  }
  function setLoading(value) {
    loading = value;
    submit.disabled = value;
    submit.classList.toggle("loading", value);
    submit.querySelector(".submit-label").textContent = value ? "Подбираем варианты" : "Подобрать подрядчиков";
    document.querySelectorAll(".demo-button, .alternative-button").forEach((button) => { button.disabled = value; });
  }
  function setStatus(state, label) {
    $("#api-settings-button").dataset.state = state;
    $("#api-status-label").textContent = label;
    $("#api-settings-button").setAttribute("aria-label", `${label}. Настройки подключения`);
    try { $("#api-status-detail").textContent = new URL(apiUrl).host; } catch (_) { $("#api-status-detail").textContent = "Проверьте адрес"; }
  }
  function normalizeUrl(value) {
    const url = new URL(value.trim());
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash) throw new Error("Укажите адрес http:// или https:// без пароля, параметров и /recommend");
    if (url.pathname.replace(/\/+$/, "").endsWith("/recommend")) throw new Error("Укажите адрес сервера без /recommend");
    return url.href.replace(/\/+$/, "");
  }
  async function readJson(response) {
    let data;
    try { data = await response.json(); } catch (_) { throw new Error("Сервер вернул неожиданный ответ. Проверьте адрес API."); }
    if (!response.ok) {
      const detail = Array.isArray(data.detail) ? data.detail.map((v) => `${v.loc?.slice(1).join(".") || "поле"}: ${v.msg}`).join("; ") : data.detail;
      const error = new Error(detail || `Ошибка сервера ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return data;
  }
  async function checkApi() {
    const currentUrl = apiUrl;
    const abort = new AbortController();
    const timer = setTimeout(() => abort.abort(), 8000);
    setStatus("checking", "Проверяем подключение");
    try {
      const data = await readJson(await fetch(`${normalizeUrl(apiUrl)}/health`, {signal: abort.signal}));
      if (currentUrl !== apiUrl) return;
      setStatus(data.semantic_ready ? "online" : "checking", data.semantic_ready ? `ИИ готов · ${data.contractors_count} профилей` : "ИИ не загружен");
    } catch (_) { if (currentUrl === apiUrl) setStatus("offline", "Сервер недоступен"); }
    finally { clearTimeout(timer); }
  }

  function fieldError(id, message) {
    const input = $(`#${id}`);
    input.classList.toggle("invalid", Boolean(message));
    input.setAttribute("aria-invalid", String(Boolean(message)));
    const target = $(`#${id}-error`);
    if (target) { target.textContent = message; input.setAttribute("aria-describedby", target.id); }
  }
  function validate() {
    let valid = true;
    const errors = {};
    [["city", "Выберите город"], ["category", "Выберите категорию"], ["event-format", "Выберите формат"]].forEach(([id, msg]) => { if (!$(`#${id}`).value) errors[id] = msg; });
    const d = $("#date").value;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(d) || d < "2026-09-23" || d > "2026-12-31") errors.date = "Дата: с 23 сентября по 31 декабря 2026";
    const budget = Number($("#budget").value);
    if (!Number.isSafeInteger(budget) || budget <= 0 || budget > 1000000000) errors.budget = "Введите целое число от 1 до 1 000 000 000";
    const duration = $("#duration").value;
    if (duration && (!Number.isInteger(Number(duration)) || Number(duration) < 1 || Number(duration) > 24)) errors.duration = "От 1 до 24 целых часов";
    if ($("#preferences").value.length > 600) errors.preferences = "До 600 символов";
    Object.values(fieldIds).filter((id) => id !== "language").forEach((id) => { fieldError(id, errors[id] || ""); if (errors[id]) valid = false; });
    if (!valid) { const first = form.querySelector(".invalid"); if (first.id === "duration") $(".extra-fields").open = true; first.focus(); }
    return valid;
  }
  function payloadFromForm() {
    const payload = {city:$("#city").value, date:$("#date").value, category:$("#category").value, event_format:$("#event-format").value, budget:Number($("#budget").value), preferences:$("#preferences").value.trim()};
    if ($("#language").value) payload.language = $("#language").value;
    if ($("#duration").value) payload.duration = Number($("#duration").value);
    return payload;
  }
  function fillForm(data) {
    Object.entries(fieldIds).forEach(([key, id]) => { $(`#${id}`).value = data[key] ?? ""; fieldError(id, ""); });
    $(".extra-fields").open = Boolean(data.language || data.duration);
    updatePreset();
  }
  function equalExceptDate(a, b) {
    return ["city","category","event_format","budget","language","duration","preferences"].every((key) => (a[key] ?? "") === (b[key] ?? ""));
  }
  function highlighted(text, evidenceText, className) {
    const el = node("p", className);
    const index = evidenceText ? text.indexOf(evidenceText) : -1;
    if (index < 0) el.textContent = text;
    else el.append(document.createTextNode(text.slice(0, index)), node("mark", "evidence-highlight", evidenceText), document.createTextNode(text.slice(index + evidenceText.length)));
    return el;
  }
  function dataFlags(c) {
    const flags = node("div", "data-flags");
    flags.append(node("span", c.synthetic ? "data-flag synthetic" : "data-flag", c.synthetic ? "Синтетический · исходный датасет" : "Анонимизированный профиль"));
    if (c.price_imputed) flags.append(node("span", "data-flag imputed", "Цена проставлена"));
    if (c.city_imputed) flags.append(node("span", "data-flag imputed", "Город проставлен"));
    return flags;
  }
  function scoreDetails(c) {
    const details = node("details", "score-details");
    if (!c.score) return details;
    details.append(node("summary", "", `Почему это место · ${c.score.total.toFixed(1)} балла`));
    details.append(node("p", "", c.score.cosine_similarity === null ? "Без пожелания: 100% оценки — запас по стартовой цене." : "85% — смысловая близость описания, 15% — запас по стартовой цене."));
    const rows = [["Смысловая близость", c.score.semantic_points], ["Запас бюджета", c.score.budget_points]];
    for (const [label, points] of rows) {
      const row = node("div", "score-row"); row.append(node("span", "", label), node("strong", "", `+${points.toFixed(1)}`)); details.append(row);
    }
    if (c.score.cosine_similarity !== null) details.append(node("p", "", `Cosine: ${c.score.cosine_similarity.toFixed(4)}; шкала = clamp((cosine − 0,65) / 0,30, 0, 1).`));
    details.append(node("p", "score-disclaimer", "Баллы объясняют порядок, а не вероятность соответствия. При равенстве: цена, затем ID."));
    return details;
  }
  function createCard(c, index, payload) {
    const article = node("article", "result-item");
    const avatar = node("div", "rank-avatar", c.name.split(/\s+/).slice(0,2).map((word) => word[0]).join(""));
    avatar.setAttribute("aria-hidden", "true");
    avatar.append(node("span", "rank-number", index + 1));
    const content = node("div", "result-content");
    const headline = node("div", "result-topline");
    headline.append(node("h3", "", c.name));
    if (!index) headline.append(node("span", "best-badge", "Первый по запросу"));
    content.append(headline, node("p", "result-location", `${c.city} · ${c.categories.join(" · ")} · ${c.id}`), dataFlags(c));
    content.append(highlighted(c.explanation, c.evidence?.text, "result-explanation"));
    if (payload.preferences) content.append(node("p", "evidence-note", "Выделено дословно из описания. Совпадение по смыслу не подтверждает все пожелания автоматически."));
    const tags = node("div", "result-tags");
    [...c.languages, ...(c.max_hours ? [`до ${c.max_hours} ч`] : ["Без привязки к часам"])] .forEach((v) => tags.append(node("span", "", v)));
    content.append(tags, scoreDetails(c));
    const price = node("div", "result-price");
    price.append(node("small", "", "стоимость от"), node("strong", "", money(c.price_from_kzt)));
    const button = node("button", "", "Профиль и факты");
    button.type = "button"; button.setAttribute("aria-label", `Профиль и факты: ${c.name}`);
    button.addEventListener("click", () => openProfile(c, payload)); price.append(button);
    article.append(avatar, content, price);
    return article;
  }
  function openProfile(c, payload) {
    const body = $("#modal-body"); body.replaceChildren();
    const title = node("h2", "", c.name); title.id = "modal-title";
    body.append(node("p", "step-label", c.id), title, dataFlags(c), highlighted(c.description, c.evidence?.text, "modal-description"));
    const facts = node("div", "modal-facts");
    for (const [label, value] of [["Цена от",money(c.price_from_kzt)],["Город",c.city],["Категории",c.categories.join(", ")],["Языки",c.languages.join(", ")],["Форматы",c.event_formats.join(", ")],["Присутствие",c.max_hours ? `До ${c.max_hours} ч` : "Не привязано к часам"]]) {
      const fact = node("div", "modal-fact"); fact.append(node("small", "", label), node("strong", "", value)); facts.append(fact);
    }
    body.append(facts, node("p", "modal-description", `Доступность ${dateText(payload.date)} проверена по календарю датасета. Итоговая стоимость требует согласования: в базе указана цена «от».`));
    c.data_notes.forEach((text) => body.append(node("p", "source-note", text)));
    body.append(scoreDetails(c));
    $("#contractor-modal").showModal();
  }
  function rejections(data, target) {
    target.replaceChildren();
    Object.entries(data.rejected || {}).sort((a,b) => b[1]-a[1]).forEach(([reason,count]) => target.append(node("span", "rejection-pill", `${reasonLabels[reason] || reason}: ${count}`)));
  }
  function comparison(data) {
    const target = $("#comparison-note"); target.replaceChildren(); target.hidden = !data;
    if (!data) return;
    target.append(node("p", "", data.message));
    if (data.now_busy.length) target.append(node("p", "", `Были в прошлой выдаче, теперь заняты: ${data.now_busy.map((c) => c.name).join(", ")}.`));
    if (data.now_available.length) target.append(node("p", "", `На прошлую дату были заняты, теперь доступны: ${data.now_available.map((c) => c.name).join(", ")}.`));
    if (!data.now_busy.length && !data.now_available.length) target.append(node("p", "", "Календарь не изменил топ-3 для этих двух дат."));
  }
  function renderSuccess(data, payload, seconds) {
    resultList.replaceChildren(...data.results.map((c,i) => createCard(c,i,payload)));
    const summary = $("#search-summary"); summary.replaceChildren();
    [payload.city,dateText(payload.date),payload.event_format,`до ${money(payload.budget)}`,payload.language,payload.duration ? `${payload.duration} ч` : ""].filter(Boolean).forEach((v) => summary.append(node("span", "summary-chip", v)));
    if (payload.preferences) summary.append(node("span", "summary-chip preference-chip", `Пожелание: ${payload.preferences}`));
    $("#ranking-caption").textContent = `${data.ranking.description} · ответ ${seconds.toFixed(2)} с`;
    $("#result-count").textContent = `${data.results.length} ${data.results.length === 1 ? "вариант" : "варианта"}`;
    $("#result-note").textContent = `${data.message} ${data.stats.busy_count ? `На дату заняты: ${data.stats.busy_count}.` : ""}`;
    $("#result-note").hidden = false;
    rejections(data, $("#rejection-list"));
    $("#rejection-scope").textContent = data.rejection_scope;
    $("#rejection-details").hidden = !Object.keys(data.rejected).length;
    setState("success");
  }
  function renderEmpty(data) {
    const absent = data.status === "category_not_found";
    $("#empty-kicker").textContent = absent ? "Категория отсутствует" : "Нет совпадений по условиям";
    $("#empty-title").textContent = absent ? "В этом городе нет такой категории" : "Ни один кандидат не прошёл все условия";
    $("#empty-message").textContent = data.message;
    rejections(data, $("#empty-rejections"));
    $("#empty-scope").textContent = absent ? "Каталог не расширяется автоматически." : data.rejection_scope;
    const list = $("#alternative-list"); list.replaceChildren();
    for (const suggestion of data.suggestions) {
      const card = node("div", "alternative-card");
      card.append(node("h5", "", suggestion.title), node("p", "", `Подходящих профилей: ${suggestion.count}. Стартовая цена от ${money(suggestion.min_price)}. Все остальные обязательные условия проверены.`));
      const button = node("button", "alternative-button", "Применить и проверить"); button.type = "button";
      button.addEventListener("click", () => { fillForm(suggestion.request); search(suggestion.request); }); card.append(button); list.append(card);
    }
    $("#alternatives").hidden = false;
    if (!data.suggestions.length) list.append(node("p", "", "В рамках проверенных изменений подтверждённого варианта нет. Попробуйте пересмотреть город, формат или несколько условий."));
    setState("empty");
  }
  async function search(payload) {
    if (loading) return;
    const requestId = ++sequence;
    controller?.abort();
    const requestController = new AbortController();
    controller = requestController;
    const signal = requestController.signal;
    const timer = setTimeout(() => requestController.abort(), 10000);
    const body = {...payload}; delete body.compare_date;
    if (previousSearch && previousSearch.date !== payload.date && equalExceptDate(previousSearch, payload)) body.compare_date = previousSearch.date;
    lastPayload = {...payload}; setLoading(true); setState("loading");
    $("#stale-note").hidden = true; $("#comparison-note").hidden = true;
    const start = performance.now();
    try {
      const data = await readJson(await fetch(`${normalizeUrl(apiUrl)}/recommend`, {method:"POST",headers:{"Content-Type":"application/json",Accept:"application/json"},body:JSON.stringify(body),signal}));
      if (requestId !== sequence) return;
      if (!Array.isArray(data.results) || !["ok","no_matches","category_not_found"].includes(data.status)) throw new Error("Неверный формат ответа сервера");
      if (data.status === "ok") renderSuccess(data,payload,(performance.now()-start)/1000); else renderEmpty(data);
      comparison(data.date_comparison); previousSearch = {...payload}; hasResult = true;
      const currentForm = payloadFromForm();
      $("#stale-note").hidden = currentForm.date === payload.date && equalExceptDate(currentForm, payload);
      setStatus("online", "Подбор выполнен");
      if (matchMedia("(max-width: 840px)").matches) $(".results-card").scrollIntoView({behavior:matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block:"start"});
    } catch (error) {
      if (requestId !== sequence) return;
      $("#error-kicker").textContent = error.status === 422 ? "Проверьте параметры" : error.status === 503 ? "ИИ-модель недоступна" : "Запрос не выполнен";
      $("#error-message").textContent = error.name === "AbortError" ? "Сервер не ответил за 10 секунд. Повторите запрос после завершения запуска." : error.message === "Failed to fetch" ? "Нет связи с сервером. Запустите START.cmd или python run.py и откройте http://127.0.0.1:8000/app/." : error.message;
      setState("error");
      if (!error.status) setStatus("offline", "Нет ответа сервера");
    } finally { clearTimeout(timer); if (requestId === sequence) setLoading(false); }
  }
  function updatePreset() { document.querySelectorAll("[data-budget]").forEach((b) => b.classList.toggle("active", b.dataset.budget === $("#budget").value)); }
  function dirty() { if (hasResult) $("#stale-note").hidden = false; updatePreset(); }
  form.addEventListener("submit", (e) => { e.preventDefault(); if (validate()) search(payloadFromForm()); });
  form.addEventListener("input", dirty); form.addEventListener("change", dirty);
  document.querySelectorAll("[data-budget]").forEach((button) => button.addEventListener("click", () => { $("#budget").value = button.dataset.budget; fieldError("budget", ""); dirty(); }));
  demos.forEach((demo) => { const button = node("button", "demo-button", demo.label); button.type = "button"; button.addEventListener("click", () => { fillForm(demo.data); if (validate()) search(payloadFromForm()); }); $("#demo-buttons").append(button); });
  $("#retry-button").addEventListener("click", () => { if (lastPayload) { fillForm(lastPayload); search(lastPayload); } });
  $("#change-filters").addEventListener("click", () => { form.scrollIntoView({block:"start",behavior:"smooth"}); $("#date").focus(); });
  function openSettings() { $("#api-url").value = apiUrl; $("#api-dialog").showModal(); }
  $("#api-settings-button").addEventListener("click", openSettings); $("#open-api-settings").addEventListener("click", openSettings);
  $("#api-form").addEventListener("submit", (e) => {
    e.preventDefault();
    try {
      const next = normalizeUrl($("#api-url").value);
      ++sequence; controller?.abort(); setLoading(false); apiUrl = next; previousSearch = null;
      try { localStorage.setItem(storageKey,apiUrl); } catch (_) { /* Private storage may be disabled. */ }
      $("#api-dialog").close(); setState("initial"); hasResult = false; $("#comparison-note").hidden = true; $("#stale-note").hidden = true; checkApi();
    } catch (error) { $("#api-url").setCustomValidity(error.message); $("#api-url").reportValidity(); }
  });
  $("#api-url").addEventListener("input", () => $("#api-url").setCustomValidity(""));
  $("[data-close-modal]").addEventListener("click", () => $("#contractor-modal").close());
  $("[data-close-api]").addEventListener("click", () => $("#api-dialog").close());
  [$("#contractor-modal"),$("#api-dialog")].forEach((dialog) => dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); }));
  checkApi();
})();
