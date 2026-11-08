const MAX_FILE_SIZE = 2 * 1024 * 1024;

const ALLOWED_UPLOAD_EXTENSIONS = new Set([
  ".txt",
  ".md",
  ".csv",
  ".pdf",
  ".docx"
]);

let currentDealId = null;

/* Авторизация */

function getToken() {
  return localStorage.getItem("slai_token") || "";
}

function getAuthHeaders() {
  const token = getToken();

  return token
    ? { "Authorization": "Bearer " + token }
    : {};
}

/* Утилиты */

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getErrorText(error) {
  if (!error) {
    return "неизвестная ошибка";
  }

  if (typeof error === "string") {
    return error;
  }

  if (typeof error === "object") {
    return error.message || error.error || JSON.stringify(error);
  }

  return String(error);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      ...getAuthHeaders()
    }
  });

  const text = await response.text();

  let data = {};

  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(`Сервер вернул некорректный JSON (${response.status})`);
  }

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem("slai_token");
      throw new Error("Требуется авторизация. Войдите в систему.");
    }

    throw new Error(
      data.error ||
      data.message ||
      `HTTP ${response.status}`
    );
  }

  return data;
}

function formatMoney(value, currency = "") {
  const amount = Number(value);

  if (!Number.isFinite(amount)) {
    return "—";
  }

  const formatted = new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 2
  }).format(amount);

  return currency ? `${formatted} ${currency}` : formatted;
}

function riskClass(severity) {
  if (severity === "high") return "risk risk-high";
  if (severity === "medium") return "risk risk-medium";
  return "risk risk-low";
}

function riskText(severity) {
  if (severity === "high") return "Высокий";
  if (severity === "medium") return "Средний";
  if (severity === "low") return "Низкий";
  return severity || "Не указан";
}

function riskLevelText(level) {
  if (level === "high") return "Высокий";
  if (level === "medium") return "Средний";
  if (level === "low") return "Низкий";
  if (level === "insufficient_data") return "Недостаточно данных";
  if (level === "missing_data") return "Недостаточно данных";
  return level || "Не указан";
}

function riskBadgeClass(level) {
  if (level === "high") return "status-badge status-high";
  if (level === "medium") return "status-badge status-medium";
  if (level === "low") return "status-badge status-low";
  return "status-badge status-medium";
}

function paymentBadgeClass(status) {
  return status === "confirmed"
    ? "status-badge status-confirmed"
    : "status-badge status-not-confirmed";
}

function paymentStatusText(status) {
  if (status === "confirmed") return "Подтверждена";
  if (status === "not_confirmed") return "Не подтверждена";
  return "Не определена";
}

function sourceText(source) {
  if (source === "deal data") return "Данные сделки";
  if (source === "uploaded document") return "Загруженный документ";
  if (source === "knowledge base") return "База знаний SLAI";
  if (source === "requires verification") return "Требует проверки";
  return source || "Источник не указан";
}

function documentTypeText(type) {
  const types = {
    contract: "Договор",
    specification: "Спецификация",
    payment: "Подтверждение депозита",
    readiness: "Готовность к отгрузке",
    quality: "Документ о качестве",
    invoice: "Инвойс",
    other: "Другое"
  };

  return types[type] || type || "Не указан";
}

function getFileExtension(fileName) {
  const normalizedName = String(fileName || "").toLowerCase();
  const dotIndex = normalizedName.lastIndexOf(".");

  if (dotIndex === -1) {
    return "";
  }

  return normalizedName.slice(dotIndex);
}

function readNumberInput(elementId) {
  const element = document.getElementById(elementId);

  if (!element) {
    throw new Error(`Элемент ${elementId} не найден`);
  }

  const rawValue = element.value.trim();

  if (rawValue === "") {
    return null;
  }

  const value = Number(rawValue.replace(",", "."));

  if (!Number.isFinite(value)) {
    throw new Error(`Поле "${elementId}" должно содержать число`);
  }

  return value;
}

function buildDealPayload() {
  return {
    supplier_name: document.getElementById("supplier_name").value.trim(),
    product_name: document.getElementById("product_name").value.trim(),
    quantity: readNumberInput("quantity"),
    unit_price: readNumberInput("unit_price"),
    currency: document.getElementById("currency").value.trim().toUpperCase(),
    incoterm: document.getElementById("incoterm").value.trim(),
    payment_terms: document.getElementById("payment_terms").value.trim(),
    production_days: readNumberInput("production_days")
  };
}

async function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = () => {
      const result = String(reader.result || "");
      const separatorIndex = result.indexOf(",");

      if (separatorIndex === -1) {
        reject(new Error("Не удалось преобразовать файл в Base64"));
        return;
      }

      resolve(result.slice(separatorIndex + 1));
    };

    reader.onerror = () => {
      reject(new Error("Не удалось прочитать файл"));
    };

    reader.readAsDataURL(file);
  });
}

/* Отчёт */

function supplierStatusText(status) {
  if (status === "approved") return "Одобрен";
  if (status === "needs_review") return "Требует проверки";
  if (status === "failed") return "Ошибка проверки";
  return "Не определён";
}

function renderSupplierAgent(data) {
  const supplier = data.supplier_agent;

  if (!supplier) {
    return "";
  }

  const supplierStatus = supplier.supplier_status || "needs_review";

  let html = `
    <div class="section">
      <h3>Проверка поставщика</h3>

      <div class="row">
        <span>Статус поставщика</span>
        <span>${escapeHtml(supplierStatusText(supplierStatus))}</span>
      </div>

      <div class="row">
        <span>Уровень риска</span>
        <span>${escapeHtml(riskLevelText(supplier.risk_level))}</span>
      </div>
  `;

  if (Array.isArray(supplier.missing_information) && supplier.missing_information.length) {
    html += `<h4>Недостающая информация</h4><ul class="list">`;

    supplier.missing_information.forEach(item => {
      html += `<li>${escapeHtml(item)}</li>`;
    });

    html += `</ul>`;
  }

  if (Array.isArray(supplier.risks) && supplier.risks.length) {
    html += `<h4>Риски поставщика</h4>`;

    supplier.risks.forEach(risk => {
      html += `
        <div class="${escapeHtml(riskClass(risk.severity))}">
          <div class="risk-title">
            ${escapeHtml(risk.title || "Риск")} —
            ${escapeHtml(riskText(risk.severity))} риск
          </div>

          <div>${escapeHtml(risk.description || "")}</div>

          <div class="risk-source">
            Источник: ${escapeHtml(sourceText(risk.source))}
          </div>
        </div>
      `;
    });
  }

  if (Array.isArray(supplier.next_actions) && supplier.next_actions.length) {
    html += `<h4>Следующие действия</h4><ul class="list">`;

    supplier.next_actions.forEach(action => {
      html += `<li>${escapeHtml(action)}</li>`;
    });

    html += `</ul>`;
  }

  if (Array.isArray(supplier.evidence) && supplier.evidence.length) {
    html += `<h4>Документы-основания</h4><ul class="list">`;

    supplier.evidence.forEach(item => {
      html += `
        <li>
          ${escapeHtml(item.file_name || "")}
          (${escapeHtml(documentTypeText(item.document_type))})
        </li>
      `;
    });

    html += `</ul>`;
  }

  html += `</div>`;

  return html;
}

function renderReport(data) {
  const report = document.getElementById("report");

  if (!report) {
    return;
  }

  const calc = data.calculation || {};
  const audit = data.audit || data;
  const message = audit.supplier_message || {};

  const currency =
    calc.currency ||
    data.currency ||
    document.getElementById("currency")?.value ||
    "";

  let html = `
    <div class="section">
      <h3>Расчёт поставки</h3>

      <div class="row">
        <span>Количество</span>
        <span>${escapeHtml(calc.quantity ?? "")}</span>
      </div>

      <div class="row">
        <span>Цена за единицу</span>
        <span>${escapeHtml(formatMoney(calc.unit_price ?? 0, currency))}</span>
      </div>

      <div class="row">
        <span>Стоимость товара</span>
        <span>${escapeHtml(formatMoney(calc.goods_cost ?? 0, currency))}</span>
      </div>

      <div class="row">
        <span>Логистика</span>
        <span>${escapeHtml(formatMoney(calc.logistics_cost ?? 0, currency))}</span>
      </div>

      <div class="row">
        <span>Таможенная пошлина</span>
        <span>${escapeHtml(formatMoney(calc.duty_cost ?? 0, currency))}</span>
      </div>

      <div class="row">
        <span>НДС</span>
        <span>${escapeHtml(formatMoney(calc.vat_cost ?? 0, currency))}</span>
      </div>

      <div class="row">
        <span>Таможенный сбор</span>
        <span>${escapeHtml(formatMoney(calc.customs_fee ?? calc.customs_cost ?? 0, currency))}</span>
      </div>

      <div class="row">
        <span>Брокерская комиссия</span>
        <span>${escapeHtml(formatMoney(calc.brokerage_fee ?? 0, currency))}</span>
      </div>

      <div class="row">
        <span>Сертификация</span>
        <span>${escapeHtml(formatMoney(calc.certification_cost ?? 0, currency))}</span>
      </div>

      <div class="row">
        <span>Прочие расходы</span>
        <span>${escapeHtml(formatMoney(calc.other_costs ?? calc.other_cost ?? 0, currency))}</span>
      </div>

      <div class="row">
        <span><strong>Итоговая стоимость</strong></span>
        <span><strong>${escapeHtml(formatMoney(calc.total_cost ?? 0, currency))}</strong></span>
      </div>

      <div class="row">
        <span>Стоимость единицы</span>
        <span>${escapeHtml(formatMoney(calc.unit_cost ?? calc.cost_per_unit ?? 0, currency))}</span>
      </div>
    </div>
  `;

  html += `
    <div class="section">
      <h3>Общий уровень риска</h3>
      <div>
        <span class="${escapeHtml(riskBadgeClass(audit.risk_level))}">
          ${escapeHtml(riskLevelText(audit.risk_level))}
        </span>
      </div>
    </div>
  `;

  if (Array.isArray(audit.missing_information) && audit.missing_information.length) {
    html += `
      <div class="section">
        <h3>Недостающие данные</h3>
        <ul class="list">
    `;

    audit.missing_information.forEach(item => {
      html += `
        <li>
          ${escapeHtml(
            typeof item === "object"
              ? item.title || item.name || item.code
              : item
          )}
        </li>
      `;
    });

    html += `</ul></div>`;
  }

  if (Array.isArray(audit.risks) && audit.risks.length) {
    html += `<div class="section"><h3>Риски</h3>`;

    audit.risks.forEach(risk => {
      html += `
        <div class="${escapeHtml(riskClass(risk.severity))}">
          <div class="risk-title">
            ${escapeHtml(risk.title || "Риск")} —
            ${escapeHtml(riskText(risk.severity))} риск
          </div>

          <div>${escapeHtml(risk.description || "")}</div>

          <div class="risk-source">
            Источник: ${escapeHtml(sourceText(risk.source))}
          </div>
        </div>
      `;
    });

    html += `</div>`;
  }

  if (Array.isArray(audit.recommendations) && audit.recommendations.length) {
    html += `
      <div class="section">
        <h3>Рекомендации</h3>
        <ul class="list">
    `;

    audit.recommendations.forEach(item => {
      html += `
        <li>
          ${escapeHtml(
            typeof item === "object"
              ? item.text || item.title || ""
              : item
          )}
        </li>
      `;
    });

    html += `</ul></div>`;
  }

  if (message.chinese || message.russian_translation) {
    html += `
      <div class="section">
        <h3>Сообщение поставщику</h3>

        <div class="message">
          <strong>Китайский:</strong><br>
          ${escapeHtml(message.chinese || "")}
        </div>

        <div class="message">
          <strong>Русский перевод:</strong><br>
          ${escapeHtml(message.russian_translation || "")}
        </div>
      </div>
    `;
  }

  const paymentAgent = data.payment_agent || audit.payment_agent || {};
  const paymentStatus = paymentAgent.payment_status || "not_confirmed";
  const paymentEvidence = paymentAgent.evidence || [];

  html += `
    <div class="section">
      <h3>Проверка оплаты</h3>

      <div class="row">
        <span>Статус оплаты</span>
        <span>
          <span class="${escapeHtml(paymentBadgeClass(paymentStatus))}">
            ${escapeHtml(paymentStatusText(paymentStatus))}
          </span>
        </span>
      </div>

      <div class="row">
        <span>Уровень риска</span>
        <span>${escapeHtml(riskLevelText(paymentAgent.risk_level || "low"))}</span>
      </div>

      <h4>Документы-основания</h4>
      <ul class="list">
  `;

  if (paymentEvidence.length) {
    paymentEvidence.forEach(item => {
      html += `
        <li>
          ${escapeHtml(item.file_name || "")}
          (${escapeHtml(documentTypeText(item.document_type))})
        </li>
      `;
    });
  } else {
    html += `<li>Документы-основания не предоставлены</li>`;
  }

  html += `</ul></div>`;

  html += renderSupplierAgent(data);

  report.innerHTML = html;
  report.classList.remove("hidden");
}

/* Действия */

async function runAudit() {
  const button = document.getElementById("runButton");
  const status = document.getElementById("status");
  const report = document.getElementById("report");

  if (!currentDealId) {
    status.innerText = "Сначала сохраните или выберите сделку";
    return;
  }

  button.disabled = true;
  status.innerText = "SLAI выполняет аудит...";
  report.classList.add("hidden");

  try {
    const payload = {
      deal_id: currentDealId,
      ...buildDealPayload()
    };

    const data = await fetchJson("/api/audit", {
      method: "POST",
      headers: {
        "Content-Type": "application/json; charset=utf-8"
      },
      body: JSON.stringify(payload)
    });

    if (data.status === "completed") {
      status.innerText = "Аудит завершён";
      renderReport(data);
      return;
    }

    if (data.status === "missing_data" || data.status === "insufficient_data") {
      status.innerText =
        "Не хватает данных: " + (data.missing_fields || []).join(", ");
      return;
    }

    const firstError =
      Array.isArray(data.errors) && data.errors.length
        ? getErrorText(data.errors[0])
        : null;

    status.innerText =
      "Ошибка: " + (firstError || data.error || "неизвестная ошибка");
  } catch (error) {
    status.innerText = "Ошибка аудита: " + getErrorText(error);
  } finally {
    button.disabled = false;
  }
}

function newDeal() {
  document.getElementById("supplier_name").value = "";
  document.getElementById("product_name").value = "";
  document.getElementById("quantity").value = "";
  document.getElementById("unit_price").value = "";
  document.getElementById("currency").value = "USD";
  document.getElementById("incoterm").value = "";
  document.getElementById("payment_terms").value = "";
  document.getElementById("production_days").value = "";

  currentDealId = null;

  const report = document.getElementById("report");

  if (report) {
    report.classList.add("hidden");
    report.innerHTML = "";
  }

  const documentsList = document.getElementById("documentsList");

  if (documentsList) {
    documentsList.innerHTML = "<p>Сначала выберите сделку.</p>";
  }

  document.getElementById("status").innerText =
    "Создана новая форма сделки. Заполните данные и нажмите «Сохранить сделку».";
}

async function saveDeal() {
  const status = document.getElementById("status");

  try {
    const payload = buildDealPayload();

    const url = currentDealId
      ? `/api/deals/${currentDealId}`
      : "/api/deals";

    const method = currentDealId ? "PUT" : "POST";

    const data = await fetchJson(url, {
      method,
      headers: {
        "Content-Type": "application/json; charset=utf-8"
      },
      body: JSON.stringify(payload)
    });

    if (data.status === "created" || data.status === "updated") {
      currentDealId = data.id ?? data.deal_id ?? currentDealId;

      status.innerText = "Сделка сохранена. Номер: " + currentDealId;

      await loadDeals();
      await loadDealDocuments();
      return;
    }

    status.innerText = "Ошибка сохранения: " + (data.error || "неизвестная ошибка");
  } catch (error) {
    status.innerText = "Ошибка сохранения: " + getErrorText(error);
  }
}

async function loadDeals() {
  const dealsList = document.getElementById("dealsList");

  try {
    const deals = await fetchJson("/api/deals");

    if (!Array.isArray(deals)) {
      throw new Error("Сервер вернул некорректный список сделок");
    }

    let html = "<p>Нажмите на сделку, чтобы открыть её.</p>";

    if (!deals.length) {
      html += "<p>Сохранённых сделок пока нет.</p>";
      dealsList.innerHTML = html;
      return;
    }

    deals.forEach(deal => {
      const dealId = Number(deal.id);

      if (!Number.isSafeInteger(dealId)) {
        return;
      }

      html += `
        <div class="row deal-row">
          <span class="deal-open" onclick="openDealById(${dealId})">
            ${escapeHtml(deal.id)} —
            ${escapeHtml(deal.supplier_name)} |
            ${escapeHtml(deal.product_name)}
          </span>

          <button class="deal-delete" onclick="deleteDealById(${dealId})">
            Удалить
          </button>
        </div>
      `;
    });

    dealsList.innerHTML = html;
  } catch (error) {
    dealsList.innerText =
      "Не удалось загрузить сделки: " + getErrorText(error);
  }
}

async function openDealById(dealId) {
  const status = document.getElementById("status");

  try {
    const deal = await fetchJson(`/api/deals/${dealId}`);

    document.getElementById("supplier_name").value = deal.supplier_name ?? "";
    document.getElementById("product_name").value = deal.product_name ?? "";
    document.getElementById("quantity").value = deal.quantity ?? "";
    document.getElementById("unit_price").value = deal.unit_price ?? "";
    document.getElementById("currency").value = deal.currency || "USD";
    document.getElementById("incoterm").value = deal.incoterm ?? "";
    document.getElementById("payment_terms").value = deal.payment_terms ?? "";
    document.getElementById("production_days").value = deal.production_days ?? "";

    currentDealId = Number(dealId);

    status.innerText =
      "Открыта сделка " + dealId +
      ". Можно изменить данные и нажать «Сохранить сделку».";

    await loadDealDocuments();
  } catch (error) {
    status.innerText = "Ошибка открытия сделки: " + getErrorText(error);
  }
}

function deleteDeal() {
  if (!currentDealId) {
    document.getElementById("status").innerText = "Сначала выберите сделку";
    return;
  }

  deleteDealById(currentDealId);
}

async function deleteDealById(dealId) {
  const status = document.getElementById("status");

  const confirmed = confirm("Точно хотите удалить сделку " + dealId + "?");

  if (!confirmed) {
    status.innerText = "Удаление сделки " + dealId + " отменено.";
    return;
  }

  try {
    const data = await fetchJson(`/api/deals/${dealId}`, {
      method: "DELETE"
    });

    if (data.status === "deleted") {
      if (Number(currentDealId) === Number(dealId)) {
        currentDealId = null;

        const report = document.getElementById("report");

        if (report) {
          report.classList.add("hidden");
          report.innerHTML = "";
        }

        const documentsList = document.getElementById("documentsList");

        if (documentsList) {
          documentsList.innerHTML = "<p>Сначала выберите сделку.</p>";
        }
      }

      status.innerText = "Сделка № " + dealId + " удалена.";
      await loadDeals();
    } else {
      status.innerText =
        "Ошибка удаления: " + (data.error || "неизвестная ошибка");
    }
  } catch (error) {
    status.innerText = "Ошибка удаления: " + getErrorText(error);
  }
}

async function uploadDocument() {
  const fileInput = document.getElementById("documentFile");
  const typeInput = document.getElementById("documentType");
  const status = document.getElementById("uploadStatus");

  if (!currentDealId) {
    status.innerText = "Сначала выберите сделку";
    return;
  }

  const file = fileInput.files[0];

  if (!file) {
    status.innerText = "Выберите файл";
    return;
  }

  if (file.size > MAX_FILE_SIZE) {
    status.innerText = "Файл слишком большой. Максимум — 2 МБ.";
    return;
  }

  const extension = getFileExtension(file.name);

  if (!ALLOWED_UPLOAD_EXTENSIONS.has(extension)) {
    status.innerText =
      "Поддерживаются только TXT, MD, CSV, PDF и DOCX.";
    return;
  }

  try {
    status.innerText = "Чтение файла...";

    const payload = {
      file_name: file.name,
      document_type: typeInput.value
    };

    if (extension === ".pdf") {
      payload.pdf_base64 = await fileToBase64(file);
    } else if (extension === ".docx") {
      payload.docx_base64 = await fileToBase64(file);
    } else {
      payload.extracted_text = await file.text();
    }

    status.innerText = "Загрузка...";

    const data = await fetchJson(
      `/api/deals/${currentDealId}/documents`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json; charset=utf-8"
        },
        body: JSON.stringify(payload)
      }
    );

    if (data.status === "uploaded") {
      status.innerText = "Документ загружен: " + data.file_name;
      fileInput.value = "";
      await loadDealDocuments();
    } else {
      status.innerText =
        "Ошибка загрузки: " + (data.error || "неизвестная ошибка");
    }
  } catch (error) {
    status.innerText = "Ошибка загрузки: " + getErrorText(error);
  }
}

async function loadDealDocuments() {
  const container = document.getElementById("documentsList");

  if (!currentDealId) {
    container.innerHTML = "<p>Сначала выберите сделку.</p>";
    return;
  }

  container.innerHTML = "<p>Загрузка документов...</p>";

  try {
    const documents = await fetchJson(
      `/api/deals/${currentDealId}/documents`
    );

    if (!Array.isArray(documents)) {
      throw new Error("Сервер вернул некорректный список документов");
    }

    if (!documents.length) {
      container.innerHTML =
        "<p>К этой сделке пока не загружены документы.</p>";
      return;
    }

    let html = "<h3>Документы сделки</h3>";

    documents.forEach(document => {
      html += `
        <div class="row">
          <span>
            ${escapeHtml(document.number ?? "")}.
            ${escapeHtml(documentTypeText(document.document_type))} —
            ${escapeHtml(document.file_name)}
          </span>

          <span>
            ${escapeHtml(document.content_length ?? 0)} символов
          </span>
        </div>
      `;
    });

    container.innerHTML = html;
  } catch (error) {
    container.innerHTML =
      "<p>Ошибка загрузки документов: " +
      escapeHtml(getErrorText(error)) +
      "</p>";
  }
}

/* Подключение кнопок */

document.addEventListener("DOMContentLoaded", () => {
  const bind = (id, handler) => {
    const element = document.getElementById(id);

    if (element) {
      element.addEventListener("click", handler);
    }
  };

  bind("newDealButton", newDeal);
  bind("saveButton", saveDeal);
  bind("deleteButton", deleteDeal);
  bind("loadDealsButton", loadDeals);
  bind("uploadButton", uploadDocument);
  bind("loadDocumentsButton", loadDealDocuments);
  bind("runButton", runAudit);

  loadDeals();
});