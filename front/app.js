(function () {
    "use strict";

    const DEFAULT_API_URL = "http://127.0.0.1:8000";
    const STORAGE_KEY = "eventmatch_api_url";
    const requestTimeoutMs = 12000;

    const form = document.querySelector("#search-form");
    const submitButton = document.querySelector("#submit-button");
    const resultsCard = document.querySelector(".results-card");
    const resultCount = document.querySelector("#result-count");
    const resultList = document.querySelector("#result-list");
    const searchSummary = document.querySelector("#search-summary");
    const rejectionDetails = document.querySelector("#rejection-details");
    const rejectionList = document.querySelector("#rejection-list");
    const contractorModal = document.querySelector("#contractor-modal");
    const modalBody = document.querySelector("#modal-body");
    const apiDialog = document.querySelector("#api-dialog");
    const apiForm = document.querySelector("#api-form");
    const apiInput = document.querySelector("#api-url");
    const apiStatusButton = document.querySelector("#api-settings-button");
    const apiStatusLabel = document.querySelector("#api-status-label");
    const apiStatusDetail = document.querySelector("#api-status-detail");

    const states = {
        initial: document.querySelector("#initial-state"),
        loading: document.querySelector("#loading-state"),
        success: document.querySelector("#success-state"),
        empty: document.querySelector("#empty-state"),
        error: document.querySelector("#error-state")
    };

    const rejectionLabels = {
        wrong_city: "Другой город",
        wrong_category: "Другая категория",
        busy: "Занят в эту дату",
        wrong_format: "Не работает с форматом",
        over_budget: "Выше бюджета",
        wrong_language: "Нет нужного языка",
        duration_too_long: "Недостаточная длительность"
    };

    let lastPayload = null;
    let apiUrl = normalizeApiUrl(
        new URLSearchParams(window.location.search).get("api") ||
        localStorage.getItem(STORAGE_KEY) ||
        DEFAULT_API_URL
    );

    function normalizeApiUrl(value) {
        return String(value || DEFAULT_API_URL).trim().replace(/\/+$/, "");
    }

    function createElement(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = String(text);
        return node;
    }

    function formatMoney(value) {
        const amount = Number(value);
        if (!Number.isFinite(amount)) return "—";
        return new Intl.NumberFormat("ru-RU").format(amount) + " ₸";
    }

    function formatDate(value) {
        if (!value) return "—";
        const parts = value.split("-");
        if (parts.length !== 3) return value;
        return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long", year: "numeric" })
            .format(new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2])));
    }

    function capitalize(value) {
        const text = String(value || "");
        return text ? text.charAt(0).toUpperCase() + text.slice(1) : text;
    }

    function initials(name) {
        const parts = String(name || "EM").trim().split(/\s+/).filter(Boolean);
        return parts.slice(0, 2).map((part) => part.charAt(0)).join("").toUpperCase() || "EM";
    }

    function showState(name) {
        Object.entries(states).forEach(([key, element]) => {
            element.hidden = key !== name;
        });
        resultsCard.setAttribute("aria-busy", name === "loading" ? "true" : "false");
        resultCount.hidden = name !== "success";
    }

    function setLoading(isLoading) {
        submitButton.disabled = isLoading;
        submitButton.classList.toggle("loading", isLoading);
        submitButton.querySelector(".submit-label").textContent = isLoading ? "Подбираем варианты" : "Подобрать подрядчиков";
    }

    function setApiStatus(state, label) {
        apiStatusButton.dataset.state = state;
        apiStatusLabel.textContent = label;
        try {
            apiStatusDetail.textContent = new URL(apiUrl).host;
        } catch (_) {
            apiStatusDetail.textContent = apiUrl;
        }
    }

    async function fetchJson(url, options) {
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), requestTimeoutMs);
        try {
            const response = await fetch(url, { ...options, signal: controller.signal });
            if (!response.ok) {
                let detail = "";
                try {
                    const body = await response.json();
                    detail = Array.isArray(body.detail)
                        ? body.detail.map((item) => item.msg).join(", ")
                        : String(body.detail || "");
                } catch (_) {
                    detail = "";
                }
                throw new Error(detail || `Сервер вернул ошибку ${response.status}`);
            }
            return await response.json();
        } finally {
            window.clearTimeout(timeout);
        }
    }

    async function checkApi() {
        setApiStatus("checking", "Проверяем сервер");
        try {
            const data = await fetchJson(`${apiUrl}/`, { method: "GET" });
            const count = Number(data.contractors_count);
            setApiStatus("online", count ? `API подключён · ${count}` : "API подключён");
            return true;
        } catch (_) {
            setApiStatus("offline", "API недоступен");
            return false;
        }
    }

    function setFieldError(id, message) {
        const input = document.querySelector(`#${id}`);
        const error = document.querySelector(`#${id}-error`);
        input.classList.toggle("invalid", Boolean(message));
        input.setAttribute("aria-invalid", message ? "true" : "false");
        if (error) error.textContent = message || "";
    }

    function validateForm() {
        const validations = [
            ["city", "Выберите город"],
            ["date", "Укажите дату"],
            ["category", "Выберите категорию"],
            ["event-format", "Выберите формат"],
            ["budget", "Укажите бюджет больше нуля"]
        ];

        let valid = true;
        validations.forEach(([id, message]) => {
            const input = document.querySelector(`#${id}`);
            const invalid = !input.value || (id === "budget" && Number(input.value) <= 0);
            setFieldError(id, invalid ? message : "");
            if (invalid) valid = false;
        });

        if (!valid) {
            const firstInvalid = form.querySelector(".invalid");
            if (firstInvalid) firstInvalid.focus();
        }
        return valid;
    }

    function buildPayload() {
        const data = new FormData(form);
        const payload = {
            city: String(data.get("city")),
            date: String(data.get("date")),
            event_format: String(data.get("event_format")),
            category: String(data.get("category")),
            budget: Number(data.get("budget"))
        };

        const duration = String(data.get("duration") || "").trim();
        const language = String(data.get("language") || "").trim();
        if (duration) payload.duration = Number(duration);
        if (language) payload.language = language;
        return payload;
    }

    function addSummaryChip(text) {
        searchSummary.appendChild(createElement("span", "summary-chip", text));
    }

    function renderSearchSummary(payload) {
        searchSummary.replaceChildren();
        addSummaryChip(payload.city);
        addSummaryChip(formatDate(payload.date));
        addSummaryChip(capitalize(payload.event_format));
        addSummaryChip(`до ${formatMoney(payload.budget)}`);
        if (payload.language) addSummaryChip(capitalize(payload.language));
        if (payload.duration) addSummaryChip(`${payload.duration} ч`);
    }

    function renderRejections(rejected, container) {
        container.replaceChildren();
        const entries = Object.entries(rejected || {}).filter(([, count]) => Number(count) > 0);
        entries
            .sort((a, b) => Number(b[1]) - Number(a[1]))
            .forEach(([reason, count]) => {
                container.appendChild(createElement("span", "rejection-pill", `${rejectionLabels[reason] || reason}: ${count}`));
            });
        return entries.length;
    }

    function createResultCard(contractor, index, payload) {
        const article = createElement("article", "result-item");
        const avatar = createElement("div", "rank-avatar", initials(contractor.name));
        avatar.appendChild(createElement("span", "rank-number", String(index + 1).padStart(2, "0")));

        const content = createElement("div", "result-content");
        const topLine = createElement("div", "result-topline");
        topLine.appendChild(createElement("h3", "", contractor.name || "Подрядчик"));
        if (index === 0) topLine.appendChild(createElement("span", "best-badge", "Лучший выбор"));
        content.appendChild(topLine);
        content.appendChild(createElement("p", "result-location", `${contractor.city} · ${(contractor.categories || []).join(" · ")}`));

        const tags = createElement("div", "result-tags");
        (contractor.event_formats || []).slice(0, 3).forEach((item) => tags.appendChild(createElement("span", "", capitalize(item))));
        (contractor.languages || []).slice(0, 3).forEach((item) => tags.appendChild(createElement("span", "", capitalize(item))));
        if (contractor.max_hours) tags.appendChild(createElement("span", "", `до ${contractor.max_hours} ч`));
        content.appendChild(tags);

        const price = createElement("div", "result-price");
        price.appendChild(createElement("small", "", "стоимость от"));
        price.appendChild(createElement("strong", "", formatMoney(contractor.price_from_kzt)));
        const detailsButton = createElement("button", "", "Подробнее");
        detailsButton.type = "button";
        detailsButton.addEventListener("click", () => openContractorModal(contractor, payload, index));
        price.appendChild(detailsButton);

        article.append(avatar, content, price);
        return article;
    }

    function addModalFact(container, label, value) {
        const fact = createElement("div", "modal-fact");
        fact.append(createElement("small", "", label), createElement("strong", "", value || "—"));
        container.appendChild(fact);
    }

    function openContractorModal(contractor, payload, index) {
        modalBody.replaceChildren();
        modalBody.appendChild(createElement("p", "step-label", index === 0 ? "Лучший выбор" : `Рекомендация №${index + 1}`));
        const title = createElement("h2", "", contractor.name || "Подрядчик");
        title.id = "modal-title";
        modalBody.appendChild(title);
        modalBody.appendChild(createElement("p", "modal-description", contractor.description || "Описание не указано."));

        const facts = createElement("div", "modal-facts");
        addModalFact(facts, "Стоимость от", formatMoney(contractor.price_from_kzt));
        addModalFact(facts, "Город", contractor.city);
        addModalFact(facts, "Категории", (contractor.categories || []).join(", "));
        addModalFact(facts, "Языки", (contractor.languages || []).map(capitalize).join(", "));
        addModalFact(facts, "Форматы", (contractor.event_formats || []).map(capitalize).join(", "));
        addModalFact(facts, "Макс. длительность", contractor.max_hours ? `${contractor.max_hours} ч` : "Не ограничена");
        modalBody.appendChild(facts);

        const why = createElement("section", "modal-why");
        why.appendChild(createElement("h3", "", "Почему подходит"));
        const list = createElement("ul");
        const reasons = [
            `Работает в городе ${payload.city}`,
            `Доступен ${formatDate(payload.date)}`,
            `Поддерживает формат «${payload.event_format}»`,
            `Стоимость укладывается в бюджет с запасом ${formatMoney(Math.max(0, payload.budget - Number(contractor.price_from_kzt)))}`
        ];
        if (payload.language) reasons.push(`Работает на языке: ${payload.language}`);
        if (payload.duration) reasons.push(`Подходит для продолжительности ${payload.duration} ч`);
        reasons.forEach((reason) => list.appendChild(createElement("li", "", reason)));
        why.appendChild(list);
        modalBody.appendChild(why);
        contractorModal.showModal();
    }

    function renderSuccess(data, payload) {
        const results = Array.isArray(data.results) ? data.results : [];
        resultList.replaceChildren();
        renderSearchSummary(payload);
        results.forEach((contractor, index) => resultList.appendChild(createResultCard(contractor, index, payload)));
        resultCount.textContent = `${results.length} ${results.length === 1 ? "вариант" : "варианта"}`;

        const rejectionCount = renderRejections(data.rejected, rejectionList);
        rejectionDetails.hidden = rejectionCount === 0;
        showState("success");
    }

    function renderEmpty(data) {
        const categoryMissing = data.status === "category_not_found";
        document.querySelector("#empty-kicker").textContent = categoryMissing ? "Категория не найдена" : "Нет точных совпадений";
        document.querySelector("#empty-title").textContent = categoryMissing ? "В этом городе пока нет таких подрядчиков" : "Условия оказались слишком строгими";
        document.querySelector("#empty-message").textContent = categoryMissing
            ? "Попробуйте выбрать другой город или близкую категорию — например, «Ведущий» вместо «Ведущий церемонии»."
            : "Измените дату, формат, язык или увеличьте бюджет, чтобы увидеть больше вариантов.";
        const count = renderRejections(data.rejected, document.querySelector("#empty-rejections"));
        document.querySelector("#empty-rejections").hidden = count === 0;
        showState("empty");
    }

    function renderError(error) {
        const message = error && error.name === "AbortError"
            ? "Сервер отвечает слишком долго. Проверьте подключение и повторите запрос."
            : (error && error.message) || "Проверьте, что backend запущен, и попробуйте ещё раз.";
        document.querySelector("#error-message").textContent = message;
        showState("error");
        setApiStatus("offline", "API недоступен");
    }

    async function requestRecommendations(payload) {
        lastPayload = payload;
        setLoading(true);
        showState("loading");
        resultCount.hidden = true;
        try {
            const data = await fetchJson(`${apiUrl}/recommend`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "Accept": "application/json" },
                body: JSON.stringify(payload)
            });
            setApiStatus("online", "API подключён");
            if (data.status === "ok" && Array.isArray(data.results) && data.results.length) {
                renderSuccess(data, payload);
            } else if (data.status === "no_matches" || data.status === "category_not_found") {
                renderEmpty(data);
            } else {
                throw new Error("Получен неожиданный ответ сервера");
            }
        } catch (error) {
            renderError(error);
        } finally {
            setLoading(false);
        }
    }

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        if (!validateForm()) return;
        requestRecommendations(buildPayload());
    });

    form.addEventListener("input", (event) => {
        if (event.target.classList.contains("invalid")) {
            const id = event.target.id;
            if (["city", "date", "category", "event-format", "budget"].includes(id)) setFieldError(id, "");
        }
    });

    document.querySelectorAll("[data-budget]").forEach((button) => {
        button.addEventListener("click", () => {
            document.querySelector("#budget").value = button.dataset.budget;
            document.querySelectorAll("[data-budget]").forEach((item) => item.classList.toggle("active", item === button));
            setFieldError("budget", "");
        });
    });

    document.querySelector("#change-filters").addEventListener("click", () => {
        form.scrollIntoView({ behavior: "smooth", block: "start" });
        document.querySelector("#budget").focus();
    });

    document.querySelector("#increase-budget").addEventListener("click", () => {
        const budget = document.querySelector("#budget");
        budget.value = Math.ceil((Number(budget.value) * 1.2) / 10000) * 10000;
        if (validateForm()) requestRecommendations(buildPayload());
    });

    document.querySelector("#retry-button").addEventListener("click", () => {
        if (lastPayload) requestRecommendations(lastPayload);
    });

    function openApiDialog() {
        apiInput.value = apiUrl;
        apiDialog.showModal();
        window.setTimeout(() => apiInput.focus(), 0);
    }

    apiStatusButton.addEventListener("click", openApiDialog);
    document.querySelector("#open-api-settings").addEventListener("click", openApiDialog);

    apiForm.addEventListener("submit", (event) => {
        event.preventDefault();
        if (!apiInput.checkValidity()) {
            apiInput.reportValidity();
            return;
        }
        apiUrl = normalizeApiUrl(apiInput.value);
        localStorage.setItem(STORAGE_KEY, apiUrl);
        apiDialog.close();
        checkApi();
    });

    document.querySelector("[data-close-modal]").addEventListener("click", () => contractorModal.close());
    document.querySelector("[data-close-api]").addEventListener("click", () => apiDialog.close());

    [contractorModal, apiDialog].forEach((dialog) => {
        dialog.addEventListener("click", (event) => {
            if (event.target === dialog) dialog.close();
        });
    });

    const today = new Date();
    const localToday = new Date(today.getTime() - today.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    document.querySelector("#date").min = localToday;
    apiInput.value = apiUrl;
    checkApi();
})();
