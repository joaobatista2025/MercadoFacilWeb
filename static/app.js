const menuButton = document.querySelector(".menu-button");
const nav = document.querySelector(".main-nav");

if (menuButton && nav) {
  menuButton.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    menuButton.setAttribute("aria-expanded", String(open));
  });
}

document.querySelectorAll("form[data-confirm]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});

document.querySelectorAll("[data-live-table-search]").forEach((input) => {
  const table = document.querySelector(input.dataset.liveTableSearch);
  const category = document.querySelector(`[data-live-category="${input.dataset.liveTableSearch}"]`);
  const status = document.querySelector(`[data-live-status="${input.dataset.liveTableSearch}"]`);
  const emptyRow = table?.querySelector("#products-empty-live");
  const rows = table ? [...table.querySelectorAll("tbody tr[data-search]")] : [];

  const filterRows = () => {
    const term = input.value
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
    const selectedCategory = category?.value || "";
    const selectedStatus = status?.value || "";
    let visible = 0;
    rows.forEach((row) => {
      const search = row.dataset.search
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase();
      const matches =
        (!term || search.includes(term)) &&
        (!selectedCategory || row.dataset.category === selectedCategory) &&
        (!selectedStatus || row.dataset.status.split(/\s+/).includes(selectedStatus));
      row.hidden = !matches;
      if (matches) visible += 1;
    });
    if (emptyRow) emptyRow.hidden = visible !== 0;
  };

  input.addEventListener("input", filterRows);
  category?.addEventListener("change", filterRows);
  status?.addEventListener("change", filterRows);
});

const saleItems = document.querySelector("#sale-items");
const addItem = document.querySelector("#add-item");
const rowTemplate = document.querySelector("#sale-row-template");
const lotsDataElement = document.querySelector("#lots-data");
const lotsData = lotsDataElement ? JSON.parse(lotsDataElement.textContent) : [];
const catalogModal = document.querySelector("#product-catalog");
const catalogSearch = document.querySelector("#product-search");
const catalogCategory = document.querySelector("#catalog-category");
const catalogItems = document.querySelectorAll(".product-catalog-item");
const catalogEmpty = document.querySelector("#catalog-empty");
const productCount = document.querySelector("#product-count");
const barcodePanel = document.querySelector(".barcode-panel");
const barcodeScan = document.querySelector("#barcode-scan");
const barcodeAdd = document.querySelector("#barcode-add");
const barcodeFeedback = document.querySelector("#barcode-feedback");
const paymentMethod = document.querySelector("#payment-method");
const cashReceivedField = document.querySelector("#cash-received-field");
const cashReceived = document.querySelector("#cash-received");
const changeTotal = document.querySelector("#change-total");
const summaryChange = document.querySelector("#summary-change");
const customerSelect = document.querySelector("#customer-select");
const loyaltyPanel = document.querySelector("#loyalty-panel");
const loyaltyBalance = document.querySelector("#loyalty-balance");
const loyaltyProgressText = document.querySelector("#loyalty-progress-text");
const loyaltyProgressBar = document.querySelector("#loyalty-progress-bar");
const couponOffer = document.querySelector("#coupon-offer");
const loyaltyCoupon = document.querySelector("#loyalty-coupon");
const couponDescription = document.querySelector("#coupon-description");
const summarySubtotalRow = document.querySelector("#summary-subtotal-row");
const summarySubtotal = document.querySelector("#summary-subtotal");
const summaryDiscountRow = document.querySelector("#summary-discount-row");
const summaryDiscount = document.querySelector("#summary-discount");
let activeSaleRow = null;
let currentSaleTotal = 0;
let currentSaleGross = 0;

function money(value) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
}

function updateSale() {
  if (!saleItems) return;
  let total = 0;
  let count = 0;
  saleItems.querySelectorAll(".sale-row").forEach((row) => {
    const select = row.querySelector(".lot-select");
    const quantity = row.querySelector(".quantity-input");
    const option = select.options[select.selectedIndex];
    const price = Number(option?.dataset.price || 0);
    const stock = Number(option?.dataset.stock || 0);
    const qty = Math.max(0, Number(quantity.value || 0));
    quantity.max = stock || "";
    const subtotal = price * qty;
    row.querySelector(".line-total strong").textContent = money(subtotal);
    total += subtotal;
    if (price > 0) count += qty;
  });
  currentSaleGross = total;
  const customer = customerSelect?.options[customerSelect.selectedIndex];
  const couponValue = Number(customer?.dataset.couponValue || 0);
  const couponEligible =
    Boolean(customer?.value) &&
    Boolean(customer?.dataset.couponId) &&
    total >= 150;
  if (loyaltyCoupon) {
    loyaltyCoupon.disabled = !couponEligible;
    if (!couponEligible) loyaltyCoupon.checked = false;
  }
  const discount = loyaltyCoupon?.checked ? couponValue : 0;
  currentSaleTotal = Math.max(0, total - discount);
  document.querySelector("#summary-items").textContent = String(count);
  document.querySelector("#summary-total").textContent = money(currentSaleTotal);
  if (summarySubtotalRow) summarySubtotalRow.hidden = discount === 0;
  if (summaryDiscountRow) summaryDiscountRow.hidden = discount === 0;
  if (summarySubtotal) summarySubtotal.textContent = money(total);
  if (summaryDiscount) summaryDiscount.textContent = `-${money(discount)}`;
  updateLoyalty();
  updatePayment();
}

function updateLoyalty() {
  if (!customerSelect || !loyaltyPanel) return;
  const customer = customerSelect.options[customerSelect.selectedIndex];
  if (!customer?.value) {
    loyaltyPanel.hidden = true;
    if (loyaltyCoupon) {
      loyaltyCoupon.checked = false;
      loyaltyCoupon.value = "";
    }
    return;
  }

  loyaltyPanel.hidden = false;
  const balance = Number(customer.dataset.balance || 0);
  const remaining = Math.max(0, 500 - balance);
  if (loyaltyBalance) loyaltyBalance.textContent = money(balance);
  if (loyaltyProgressText) {
    loyaltyProgressText.textContent =
      remaining > 0
        ? `Faltam ${money(remaining)} para ganhar R$ 15`
        : "Meta alcançada";
  }
  if (loyaltyProgressBar) {
    loyaltyProgressBar.style.width = `${Math.min(100, (balance / 500) * 100)}%`;
  }

  const couponId = customer.dataset.couponId;
  if (!couponId) {
    if (couponOffer) couponOffer.hidden = true;
    if (loyaltyCoupon) {
      loyaltyCoupon.checked = false;
      loyaltyCoupon.value = "";
    }
    return;
  }

  if (couponOffer) couponOffer.hidden = false;
  if (loyaltyCoupon) loyaltyCoupon.value = couponId;
  const expiry = customer.dataset.couponExpiry
    ? new Date(`${customer.dataset.couponExpiry}T12:00:00`).toLocaleDateString("pt-BR")
    : "";
  if (couponDescription) {
    couponDescription.textContent =
      currentSaleGross >= 150
        ? `Disponível até ${expiry}. Compra mínima atendida.`
        : `Disponível até ${expiry}. Faltam ${money(150 - currentSaleGross)} na compra para usar.`;
  }
}

function updatePayment() {
  if (!paymentMethod) return;
  const isCash = paymentMethod.value === "dinheiro";
  if (cashReceivedField) cashReceivedField.hidden = !isCash;
  if (changeTotal) changeTotal.hidden = !isCash;
  if (cashReceived) {
    cashReceived.required = isCash;
    if (!isCash) cashReceived.value = "";
  }
  const received = Number(cashReceived?.value || 0);
  const change = isCash ? Math.max(0, received - currentSaleTotal) : 0;
  if (summaryChange) summaryChange.textContent = money(change);
}

function closeCatalog() {
  if (!catalogModal) return;
  catalogModal.classList.remove("open");
  catalogModal.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
  activeSaleRow = null;
}

function filterCatalog() {
  const term = (catalogSearch?.value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
  const category = catalogCategory?.value || "";
  let visible = 0;
  catalogItems.forEach((item) => {
    const search = item.dataset.search
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
    const show =
      (!term || search.includes(term)) &&
      (!category || item.dataset.category === category);
    item.hidden = !show;
    if (show) visible += 1;
  });
  if (productCount) productCount.textContent = String(visible);
  if (catalogEmpty) catalogEmpty.hidden = visible !== 0;
}

function openCatalog(row) {
  if (!catalogModal) return;
  activeSaleRow = row;
  catalogModal.classList.add("open");
  catalogModal.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  if (catalogSearch) {
    catalogSearch.value = "";
    if (catalogCategory) catalogCategory.value = "";
    filterCatalog();
    catalogSearch.focus();
  }
}

function normalizeScan(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "");
}

function showBarcodeFeedback(message, type = "") {
  if (!barcodeFeedback || !barcodePanel) return;
  barcodeFeedback.textContent = message;
  barcodePanel.classList.remove("success", "error");
  if (type) barcodePanel.classList.add(type);
}

function catalogItemByProductId(productId) {
  return [...catalogItems].find((item) => Number(item.dataset.productId) === Number(productId));
}

function applyProductToRow(row, item) {
  const productId = Number(item.dataset.productId);
  row.dataset.productId = String(productId);
  row.querySelector(".selected-product").textContent = item.dataset.productName;
  row.querySelector(".product-picker-button small").textContent =
    "Produto selecionado · clique para trocar";
  populateLots(row, productId);
}

function writableSaleRow() {
  const emptyRow = [...saleItems.querySelectorAll(".sale-row")].find((row) => {
    const lot = row.querySelector(".lot-select");
    return !row.dataset.productId && !lot.value;
  });
  if (emptyRow) return emptyRow;
  const fragment = rowTemplate.content.cloneNode(true);
  const row = fragment.querySelector(".sale-row");
  bindRow(row);
  saleItems.appendChild(fragment);
  return row;
}

function incrementExistingLot(lotId) {
  const existing = [...saleItems.querySelectorAll(".sale-row")].find(
    (row) => row.querySelector(".lot-select").value === String(lotId),
  );
  if (!existing) return false;
  const quantity = existing.querySelector(".quantity-input");
  quantity.value = String(Number(quantity.value || 0) + 1);
  quantity.focus();
  quantity.select();
  updateSale();
  return true;
}

function handleBarcodeScan() {
  if (!barcodeScan || !saleItems || !rowTemplate) return;
  const code = normalizeScan(barcodeScan.value);
  if (!code) {
    showBarcodeFeedback("Passe o leitor USB ou digite um código.", "error");
    return;
  }

  const lot = lotsData.find(
    (item) => normalizeScan(item.barcode) === code || normalizeScan(item.code) === code,
  );
  if (lot) {
    if (incrementExistingLot(lot.id)) {
      showBarcodeFeedback(`Mais 1 unidade adicionada ao lote ${lot.code}.`, "success");
      barcodeScan.value = "";
      return;
    }
    const productItem = catalogItemByProductId(lot.productId);
    if (!productItem) {
      showBarcodeFeedback("Lote encontrado, mas o produto não está disponível para venda.", "error");
      return;
    }
    const row = writableSaleRow();
    applyProductToRow(row, productItem);
    row.querySelector(".lot-select").value = String(lot.id);
    row.querySelector(".quantity-input").focus();
    row.querySelector(".quantity-input").select();
    updateSale();
    showBarcodeFeedback(`Lote ${lot.code} selecionado automaticamente.`, "success");
    barcodeScan.value = "";
    return;
  }

  const productItem = [...catalogItems].find(
    (item) =>
      normalizeScan(item.dataset.barcode) === code ||
      normalizeScan(item.dataset.productCode) === code,
  );
  if (productItem) {
    const row = writableSaleRow();
    applyProductToRow(row, productItem);
    row.querySelector(".lot-select").focus();
    updateSale();
    showBarcodeFeedback(
      "Produto encontrado. Agora confirme o lote impresso na embalagem.",
      "success",
    );
    barcodeScan.value = "";
    return;
  }

  showBarcodeFeedback("Código não encontrado no cadastro de produtos ou lotes.", "error");
}

function populateLots(row, productId) {
  const lotSelect = row.querySelector(".lot-select");
  const availableLots = lotsData.filter((lot) => lot.productId === productId);
  lotSelect.innerHTML = "";
  if (!availableLots.length) {
    lotSelect.append(new Option("Nenhum lote disponível", ""));
    lotSelect.disabled = true;
    return;
  }
  lotSelect.append(new Option("Selecione o código da embalagem", ""));
  availableLots.forEach((lot, index) => {
    const expiry = lot.expiry
      ? new Date(`${lot.expiry}T12:00:00`).toLocaleDateString("pt-BR")
      : "sem validade";
    const recommendation = index === 0 && lot.expiry ? " · validade mais próxima" : "";
    const option = new Option(
      `${lot.code} · ${lot.supplier} · ${expiry} · ${lot.stock} un.${recommendation}`,
      String(lot.id),
    );
    option.dataset.price = String(lot.price);
    option.dataset.stock = String(lot.stock);
    lotSelect.append(option);
  });
  lotSelect.disabled = false;
}

function bindRow(row) {
  row.querySelector(".product-picker-button").addEventListener("click", () => openCatalog(row));
  row.querySelectorAll("select, input").forEach((field) => {
    field.addEventListener("input", updateSale);
    field.addEventListener("change", updateSale);
  });
  row.querySelector(".remove-item")?.addEventListener("click", () => {
    const rows = saleItems.querySelectorAll(".sale-row");
    if (rows.length === 1) {
      row.dataset.productId = "";
      row.querySelector(".selected-product").textContent = "Escolher produto";
      row.querySelector(".product-picker-button small").textContent = "Clique para abrir o catálogo";
      row.querySelector(".lot-select").innerHTML = '<option value="">Escolha primeiro o produto</option>';
      row.querySelector(".lot-select").disabled = true;
      row.querySelector(".quantity-input").value = "1";
    } else {
      row.remove();
    }
    updateSale();
  });
}

catalogSearch?.addEventListener("input", filterCatalog);
catalogCategory?.addEventListener("change", filterCatalog);
paymentMethod?.addEventListener("change", updatePayment);
cashReceived?.addEventListener("input", updatePayment);
customerSelect?.addEventListener("change", () => {
  if (loyaltyCoupon) loyaltyCoupon.checked = false;
  updateSale();
});
loyaltyCoupon?.addEventListener("change", updateSale);
document.querySelector(".catalog-close")?.addEventListener("click", closeCatalog);
document.querySelector(".catalog-backdrop")?.addEventListener("click", closeCatalog);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && catalogModal?.classList.contains("open")) closeCatalog();
});

catalogItems.forEach((item) => {
  item.addEventListener("click", () => {
    if (!activeSaleRow) return;
    applyProductToRow(activeSaleRow, item);
    activeSaleRow.querySelector(".lot-select").focus();
    updateSale();
    closeCatalog();
  });
});

barcodeAdd?.addEventListener("click", handleBarcodeScan);
barcodeScan?.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    handleBarcodeScan();
  }
});

if (saleItems && addItem && rowTemplate) {
  saleItems.querySelectorAll(".sale-row").forEach(bindRow);
  addItem.addEventListener("click", () => {
    const fragment = rowTemplate.content.cloneNode(true);
    const row = fragment.querySelector(".sale-row");
    bindRow(row);
    saleItems.appendChild(fragment);
    openCatalog(row);
    updateSale();
  });
  updateSale();
}
