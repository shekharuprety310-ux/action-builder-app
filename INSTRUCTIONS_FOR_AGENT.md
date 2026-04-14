# Instructions for Code Agent — Action Builders Scope Builder Enhancement

## What to do
Add **pricing data, a price selector modal, cost control panel, and enhanced Excel export** to the existing `index.html` webapp.

You have been given 2 files:
- `price_data.js` — All pricing data extracted from the Deep Dive Excel (Trade + Products price lists)
- `INSTRUCTIONS_FOR_AGENT.md` — This file

---

## Step 1 — Add `price_data.js` to the project

Place `price_data.js` in the same folder as `index.html`.

In `index.html`, find this line:
```html
<script src="https://cdn.sheetjs.com/xlsx-0.20.1/package/dist/xlsx.full.min.js"></script>
```

Add immediately after it:
```html
<script src="price_data.js"></script>
```

---

## Step 2 — Add CSS (paste inside `<style>` tag, just before `</style>`)

```css
/* === PRICING MODAL === */
.price-modal-overlay {
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,0.7); z-index: 2000;
  align-items: center; justify-content: center; padding: 16px;
}
.price-modal-overlay.show { display: flex; }
.price-modal {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 14px; width: 100%; max-width: 640px; max-height: 85vh;
  display: flex; flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5); overflow: hidden;
}
.price-modal-header {
  padding: 18px 20px 14px; border-bottom: 1px solid var(--border);
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 12px; flex-shrink: 0;
}
.price-modal-title { font-size: 15px; font-weight: 700; color: var(--text); }
.price-modal-sub { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.price-modal-close {
  background: none; border: none; color: var(--text-muted);
  font-size: 22px; cursor: pointer; line-height: 1; padding: 2px 6px;
  border-radius: 6px; flex-shrink: 0;
}
.price-modal-close:hover { background: var(--surface2); color: var(--text); }
.price-modal-body { overflow-y: auto; flex: 1; padding: 0; }
.price-modal-footer {
  padding: 14px 20px; border-top: 1px solid var(--border);
  display: flex; gap: 10px; align-items: center; justify-content: flex-end;
  flex-shrink: 0; background: var(--surface);
}
.price-section-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.08em; color: var(--text-muted);
  padding: 12px 20px 6px; background: var(--surface2);
  border-bottom: 1px solid var(--border);
}
.price-option {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 12px 20px; border-bottom: 1px solid rgba(58,80,112,0.4);
  cursor: pointer; transition: background 0.15s;
}
.price-option:hover { background: var(--surface2); }
.price-option.selected {
  background: rgba(212,168,83,0.1);
  border-left: 3px solid var(--primary); padding-left: 17px;
}
.price-option input[type="radio"] {
  accent-color: var(--primary); flex-shrink: 0;
  margin-top: 3px; width: 16px; height: 16px; cursor: pointer;
}
.price-option-info { flex: 1; min-width: 0; }
.price-option-name { font-size: 13px; font-weight: 500; color: var(--text); line-height: 1.35; }
.price-option-detail { font-size: 11px; color: var(--text-muted); margin-top: 3px; line-height: 1.4; }
.price-option-code { font-size: 10px; color: var(--primary); font-family: 'DM Mono', monospace; margin-top: 2px; }
.price-option-right { text-align: right; flex-shrink: 0; }
.price-option-price { font-size: 15px; font-weight: 700; color: var(--primary); font-family: 'DM Mono', monospace; }
.price-option-uom { font-size: 10px; color: var(--text-muted); margin-top: 2px; }
.tier-badge {
  display: inline-block; font-size: 9px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.06em;
  padding: 2px 6px; border-radius: 4px; margin-left: 6px; vertical-align: middle;
}
.tier-Essentials { background: rgba(76,175,136,0.15); color: #4caf88; }
.tier-Lifestyle  { background: rgba(91,124,206,0.15);  color: #5b7cce; }
.tier-Premium    { background: rgba(212,168,83,0.15);  color: var(--primary); }
.tier-Prestige   { background: rgba(155,109,209,0.15); color: #9b6dd1; }
.tier-Standard   { background: rgba(138,157,181,0.15); color: var(--text-muted); }
.price-no-data { padding: 32px 20px; text-align: center; color: var(--text-muted); font-size: 13px; }

.item-row-price {
  font-size: 11px; color: var(--primary); font-family: 'DM Mono', monospace;
  font-weight: 600; white-space: nowrap; cursor: pointer;
  background: rgba(212,168,83,0.08); border: 1px solid rgba(212,168,83,0.25);
  border-radius: 5px; padding: 3px 7px; transition: background 0.15s;
  align-self: center; flex-shrink: 0;
}
.item-row-price:hover { background: rgba(212,168,83,0.2); }
.item-row-price.unset { color: var(--text-muted); border-color: rgba(138,157,181,0.2); background: transparent; font-size: 10px; }

/* === COST CONTROL PANEL === */
.cost-control-bar {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 16px 20px; margin-bottom: 16px;
}
.cost-control-bar-top {
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px; flex-wrap: wrap;
}
.cost-total-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); }
.cost-total-value { font-size: 28px; font-weight: 800; color: var(--primary); font-family: 'DM Mono', monospace; letter-spacing: -0.02em; }
.cost-total-gst { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.cost-breakdown-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 8px; margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--border);
}
.cost-cc-chip { background: var(--surface2); border-radius: 8px; padding: 8px 12px; display: flex; flex-direction: column; gap: 2px; }
.cost-cc-name { font-size: 11px; color: var(--text-muted); font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cost-cc-amount { font-size: 14px; font-weight: 700; color: var(--text); font-family: 'DM Mono', monospace; }
.cost-cc-items { font-size: 10px; color: var(--text-muted); }
.cost-unpriced-banner {
  background: rgba(245,166,35,0.1); border: 1px solid rgba(245,166,35,0.3);
  border-radius: 8px; padding: 8px 14px; font-size: 12px; color: var(--warning);
  margin-top: 12px; display: none;
}
.cost-unpriced-banner.show { display: block; }
```

---

## Step 3 — Add HTML (paste just before the closing `</body>` tag)

```html
<!-- Price Selector Modal -->
<div class="price-modal-overlay" id="priceModalOverlay">
  <div class="price-modal">
    <div class="price-modal-header">
      <div>
        <div class="price-modal-title" id="priceModalTitle">Select Price</div>
        <div class="price-modal-sub" id="priceModalSub"></div>
      </div>
      <button class="price-modal-close" onclick="closePriceModal()">×</button>
    </div>
    <div class="price-modal-body" id="priceModalBody"></div>
    <div class="price-modal-footer">
      <button class="btn btn-secondary" onclick="clearItemPrice()">Clear Price</button>
      <button class="btn btn-primary" onclick="confirmPriceSelection()">Confirm</button>
    </div>
  </div>
</div>
```

---

## Step 4 — Add JavaScript (paste just before the closing `</script>` tag at the bottom of the file)

```javascript
// ====================================================
// PRICING SYSTEM
// ====================================================

// itemPricing[ccName][idx] = { price, uom, description, supplier, productCode }
let itemPricing = {};
let priceModal_ccName = null;
let priceModal_idx = null;
let priceModal_selectedPrice = null;

// --- Map cost centres to their price data keys ---
const CC_TO_TRADE_KEY = {
  'Balustrade':         'Balustrade',
  'Bricks & Blocks':   'Bricks & Blocks',
  'Painting & Rendering': 'Painting & Rendering',
  'Tiling':            'Tiling',
  'Concreting':        'Concreting',
  'Electrical':        'Electrical',
  'Electrical Fittings': 'Electrical',
  'Electrical Mains':  'Electrical',
  'Heating':           'Heating',
  'Plumbing':          'Plumbing',
  'Plumb Fit':         'Plumbing',
  'Roofing':           'Roofing',
  'Roof Frame':        'Roofing',
};

const CC_TO_PRODUCT_KEY = {
  'Appliances':  ['OVENS','COOKTOPS','RANGEHOODS','DISHWASHERS','FRIDGES','WASHING MACHINES','DRYERS'],
  'Tiling - All': ['TILES'],
  'Tiling':      ['TILES'],
  'Floor Covering': ['TILES'],
};

// --- Override renderItems to add price tags ---
const _origRenderItems = renderItems;
function renderItems(ccName, query) {
  _origRenderItems(ccName, query);
  // After original render, inject price buttons
  if (!itemPricing[ccName]) itemPricing[ccName] = {};
  const body = document.getElementById('itemsBody');
  const rows = body.querySelectorAll('.item-row');
  rows.forEach(row => {
    const idx = parseInt(row.dataset.idx);
    if (isNaN(idx)) return;
    const pricing = itemPricing[ccName][idx];
    const btn = document.createElement('span');
    btn.className = 'item-row-price' + (pricing ? '' : ' unset');
    btn.textContent = pricing ? '$' + pricing.price.toLocaleString('en-AU', {minimumFractionDigits:0, maximumFractionDigits:2}) + ' / ' + (pricing.uom || 'ea') : '+ Price';
    btn.onclick = (e) => { e.stopPropagation(); openPriceModal(ccName, idx); };
    row.appendChild(btn);
  });
}

function openPriceModal(ccName, idx) {
  priceModal_ccName = ccName;
  priceModal_idx = idx;
  priceModal_selectedPrice = itemPricing[ccName] && itemPricing[ccName][idx] ? {...itemPricing[ccName][idx]} : null;

  const item = COST_CENTRES[ccName].items[idx];
  document.getElementById('priceModalTitle').textContent = item.name;
  document.getElementById('priceModalSub').textContent = ccName + (item.type ? ' · ' + item.type : '');

  const body = document.getElementById('priceModalBody');
  body.innerHTML = '';

  // Try product options first
  const prodKeys = CC_TO_PRODUCT_KEY[ccName];
  if (prodKeys) {
    let hasAny = false;
    prodKeys.forEach(pKey => {
      const opts = (PRICE_DATA.products[pKey] || []).filter(o => o.p !== null);
      if (!opts.length) return;
      hasAny = true;
      const label = document.createElement('div');
      label.className = 'price-section-label';
      label.textContent = pKey;
      body.appendChild(label);

      let lastTier = null;
      opts.forEach((opt, oi) => {
        if (opt.t !== lastTier) {
          lastTier = opt.t;
          const tierLabel = document.createElement('div');
          tierLabel.className = 'price-section-label';
          tierLabel.style.background = 'transparent';
          tierLabel.style.paddingLeft = '20px';
          tierLabel.innerHTML = `<span class="tier-badge tier-${opt.t}">${opt.t}</span>`;
          body.appendChild(tierLabel);
        }
        const isSelected = priceModal_selectedPrice && priceModal_selectedPrice._key === pKey + '_' + oi;
        const row = document.createElement('div');
        row.className = 'price-option' + (isSelected ? ' selected' : '');
        row.innerHTML = `
          <input type="radio" name="priceOpt" ${isSelected ? 'checked' : ''}>
          <div class="price-option-info">
            <div class="price-option-name">${opt.d}</div>
            ${opt.f ? '<div class="price-option-detail">' + opt.f + '</div>' : ''}
            ${opt.c ? '<div class="price-option-code">Code: ' + opt.c + '</div>' : ''}
          </div>
          <div class="price-option-right">
            <div class="price-option-price">$${Number(opt.p).toLocaleString('en-AU',{minimumFractionDigits:0,maximumFractionDigits:2})}</div>
            <div class="price-option-uom">${opt.u || 'ea'}</div>
          </div>`;
        row.onclick = () => {
          body.querySelectorAll('.price-option').forEach(r => { r.classList.remove('selected'); r.querySelector('input').checked = false; });
          row.classList.add('selected'); row.querySelector('input').checked = true;
          priceModal_selectedPrice = { price: opt.p, uom: opt.u || 'ea', description: opt.d, supplier: opt.s, productCode: opt.c, _key: pKey + '_' + oi };
        };
        body.appendChild(row);
      });
    });
    if (!hasAny) body.innerHTML = '<div class="price-no-data">No product pricing available for this item.<br>You can enter a custom price below.</div>';
  } else {
    // Trade options
    const tradeKey = CC_TO_TRADE_KEY[ccName];
    const tradeItems = tradeKey ? (PRICE_DATA.trade[tradeKey] || []).filter(o => typeof o.p === 'number') : [];

    // Filter by item name similarity
    const itemNameLower = item.name.toLowerCase();
    const keywords = itemNameLower.replace(/supply and install|supply|install|and|&|the|of|a|an/g, ' ').trim().split(/\s+/).filter(w => w.length > 3);
    
    let filtered = tradeItems;
    if (keywords.length) {
      filtered = tradeItems.filter(t => keywords.some(k => t.d.toLowerCase().includes(k)));
      if (!filtered.length) filtered = tradeItems.slice(0, 30); // fallback: show all
    }

    if (!filtered.length) {
      body.innerHTML = '<div class="price-no-data">No trade pricing found. Enter a custom price.</div>';
    } else {
      const label = document.createElement('div');
      label.className = 'price-section-label';
      label.textContent = (tradeKey || ccName) + ' — Trade Rates (EX GST)';
      body.appendChild(label);

      filtered.forEach((opt, oi) => {
        const isSelected = priceModal_selectedPrice && priceModal_selectedPrice._key === 'trade_' + oi;
        const row = document.createElement('div');
        row.className = 'price-option' + (isSelected ? ' selected' : '');
        row.innerHTML = `
          <input type="radio" name="priceOpt" ${isSelected ? 'checked' : ''}>
          <div class="price-option-info">
            <div class="price-option-name">${opt.d}</div>
            ${opt.s ? '<div class="price-option-detail">Supplier: ' + opt.s + '</div>' : ''}
          </div>
          <div class="price-option-right">
            <div class="price-option-price">$${Number(opt.p).toLocaleString('en-AU',{minimumFractionDigits:0,maximumFractionDigits:2})}</div>
            <div class="price-option-uom">${opt.u || 'ea'}</div>
          </div>`;
        row.onclick = () => {
          body.querySelectorAll('.price-option').forEach(r => { r.classList.remove('selected'); r.querySelector('input').checked = false; });
          row.classList.add('selected'); row.querySelector('input').checked = true;
          priceModal_selectedPrice = { price: opt.p, uom: opt.u || 'ea', description: opt.d, supplier: opt.s, productCode: '', _key: 'trade_' + oi };
        };
        body.appendChild(row);
      });
    }
  }

  // Custom price input at bottom
  const customSection = document.createElement('div');
  customSection.innerHTML = `
    <div class="price-section-label">Custom Price (EX GST)</div>
    <div style="padding:14px 20px;display:flex;gap:10px;align-items:center">
      <span style="color:var(--primary);font-size:16px;font-weight:700">$</span>
      <input type="number" id="customPriceInput" min="0" step="0.01"
        value="${priceModal_selectedPrice && priceModal_selectedPrice._key === 'custom' ? priceModal_selectedPrice.price : ''}"
        placeholder="Enter amount..."
        style="flex:1;background:var(--surface2);border:1.5px solid var(--border);border-radius:8px;padding:10px 12px;font-size:14px;color:var(--text);outline:none;font-family:'DM Mono',monospace">
      <input type="text" id="customUomInput"
        value="${priceModal_selectedPrice && priceModal_selectedPrice._key === 'custom' ? priceModal_selectedPrice.uom : 'ea'}"
        placeholder="UOM"
        style="width:70px;background:var(--surface2);border:1.5px solid var(--border);border-radius:8px;padding:10px 10px;font-size:13px;color:var(--text);outline:none">
    </div>`;
  body.appendChild(customSection);

  document.getElementById('priceModalOverlay').classList.add('show');
}

function closePriceModal() {
  document.getElementById('priceModalOverlay').classList.remove('show');
  priceModal_ccName = null;
  priceModal_idx = null;
  priceModal_selectedPrice = null;
}

function clearItemPrice() {
  if (!priceModal_ccName || priceModal_idx === null) return;
  if (!itemPricing[priceModal_ccName]) itemPricing[priceModal_ccName] = {};
  delete itemPricing[priceModal_ccName][priceModal_idx];
  closePriceModal();
  renderItems(priceModal_ccName || activeCCName, document.getElementById('itemSearch') ? document.getElementById('itemSearch').value : '');
  updateCostControl();
}

function confirmPriceSelection() {
  if (!priceModal_ccName || priceModal_idx === null) return;
  if (!itemPricing[priceModal_ccName]) itemPricing[priceModal_ccName] = {};

  const customVal = document.getElementById('customPriceInput') ? parseFloat(document.getElementById('customPriceInput').value) : NaN;
  const customUom = document.getElementById('customUomInput') ? document.getElementById('customUomInput').value.trim() : 'ea';

  if (!isNaN(customVal) && customVal > 0 && (!priceModal_selectedPrice || priceModal_selectedPrice._key === 'custom')) {
    itemPricing[priceModal_ccName][priceModal_idx] = { price: customVal, uom: customUom || 'ea', description: 'Custom price', supplier: '', productCode: '', _key: 'custom' };
  } else if (!isNaN(customVal) && customVal > 0 && document.getElementById('customPriceInput').value !== '') {
    // custom overrides radio
    itemPricing[priceModal_ccName][priceModal_idx] = { price: customVal, uom: customUom || 'ea', description: 'Custom price', supplier: '', productCode: '', _key: 'custom' };
  } else if (priceModal_selectedPrice) {
    itemPricing[priceModal_ccName][priceModal_idx] = priceModal_selectedPrice;
  }

  const saved = priceModal_ccName;
  closePriceModal();
  renderItems(saved, document.getElementById('itemSearch') ? document.getElementById('itemSearch').value : '');
  updateCostControl();
  showToast('Price saved', 'success');
}

// ====================================================
// COST CONTROL PANEL
// ====================================================

function updateCostControl() {
  const panel = document.getElementById('costControlPanel');
  if (!panel) return;

  let grandTotal = 0;
  let unpriced = 0;
  const ccTotals = {};

  [...selectedCC].forEach(ccName => {
    const ccSel = itemSelections[ccName];
    if (!ccSel) return;
    const checked = Object.entries(ccSel).filter(([, v]) => v.checked);
    if (!checked.length) return;
    let ccTotal = 0;
    checked.forEach(([idx, v]) => {
      const pricing = itemPricing[ccName] && itemPricing[ccName][idx];
      const qty = parseFloat(v.qty) || 1;
      if (pricing && typeof pricing.price === 'number') {
        ccTotal += pricing.price * qty;
      } else {
        unpriced++;
      }
    });
    ccTotals[ccName] = { total: ccTotal, count: checked.length };
    grandTotal += ccTotal;
  });

  const gst = grandTotal * 0.1;
  document.getElementById('ccGrandTotal').textContent = '$' + grandTotal.toLocaleString('en-AU', {minimumFractionDigits:0, maximumFractionDigits:0});
  document.getElementById('ccGstTotal').textContent = '+ GST $' + gst.toLocaleString('en-AU', {minimumFractionDigits:0, maximumFractionDigits:0}) + '  =  $' + (grandTotal + gst).toLocaleString('en-AU', {minimumFractionDigits:0, maximumFractionDigits:0}) + ' inc. GST';

  const grid = document.getElementById('ccBreakdownGrid');
  grid.innerHTML = '';
  Object.entries(ccTotals).forEach(([ccName, data]) => {
    const chip = document.createElement('div');
    chip.className = 'cost-cc-chip';
    chip.innerHTML = `<div class="cost-cc-name">${ccName}</div>
      <div class="cost-cc-amount">${data.total > 0 ? '$' + data.total.toLocaleString('en-AU',{minimumFractionDigits:0,maximumFractionDigits:0}) : '—'}</div>
      <div class="cost-cc-items">${data.count} item${data.count !== 1 ? 's' : ''}</div>`;
    grid.appendChild(chip);
  });

  const banner = document.getElementById('ccUnpricedBanner');
  if (unpriced > 0) {
    banner.textContent = `⚠ ${unpriced} item${unpriced !== 1 ? 's' : ''} not yet priced — totals are partial`;
    banner.classList.add('show');
  } else {
    banner.classList.remove('show');
  }
}

// Hook into goToStep to update cost panel when entering Step 4
const _origGoToStep = goToStep;
function goToStep(n) {
  _origGoToStep(n);
  if (n === 4) setTimeout(updateCostControl, 100);
}

// ====================================================
// ENHANCED EXCEL EXPORT WITH PRICING
// ====================================================

function exportWithPricing() {
  const proj = {
    client: getVal('projClient'),
    name: getVal('projName'),
    location: getVal('projLocation'),
    type: getVal('projType'),
    date: getVal('projDate'),
    num: getVal('projNum')
  };

  const wb = XLSX.utils.book_new();

  // --- Sheet 1: Detailed Scope with Pricing ---
  const wsData = [
    ['Action Builders — Scope with Cost Control'],
    ['Client', proj.client || '', 'Project', proj.name || ''],
    ['Location', proj.location || '', 'Date', proj.date || ''],
    ['Reference', proj.num || '', 'Type', proj.type || ''],
    [],
    ['Cost Centre', 'Item', 'Type', 'Category', 'Qty', 'UOM', 'Unit Price (EX GST)', 'Line Total (EX GST)', 'GST', 'Total INC GST', 'Supplier', 'Product Code', 'Notes']
  ];

  let grandTotal = 0;
  let unpriced = 0;

  [...selectedCC].forEach(ccName => {
    const ccSel = itemSelections[ccName];
    if (!ccSel) return;
    const checked = Object.entries(ccSel).filter(([, v]) => v.checked);
    if (!checked.length) return;
    const ccData = COST_CENTRES[ccName];

    checked.forEach(([idx, v]) => {
      const item = ccData.items[parseInt(idx)];
      const qty = parseFloat(v.qty) || 1;
      const pricing = itemPricing[ccName] && itemPricing[ccName][idx];
      const unitPrice = pricing && typeof pricing.price === 'number' ? pricing.price : null;
      const lineTotal = unitPrice !== null ? unitPrice * qty : null;
      const gst = lineTotal !== null ? lineTotal * 0.1 : null;
      const totalInc = lineTotal !== null ? lineTotal * 1.1 : null;

      if (lineTotal !== null) grandTotal += lineTotal;
      else unpriced++;

      wsData.push([
        ccName,
        item.name,
        item.type || '',
        item.category || '',
        qty,
        pricing ? pricing.uom : '',
        unitPrice !== null ? unitPrice : 'Not priced',
        lineTotal !== null ? lineTotal : '',
        gst !== null ? gst : '',
        totalInc !== null ? totalInc : '',
        pricing ? pricing.supplier : '',
        pricing ? pricing.productCode : '',
        v.notes || ''
      ]);
    });
  });

  // Totals row
  wsData.push([]);
  wsData.push(['', '', '', '', '', '', 'SUBTOTAL (EX GST)', grandTotal, grandTotal * 0.1, grandTotal * 1.1, '', '', unpriced > 0 ? `NOTE: ${unpriced} items not priced` : '']);

  const ws1 = XLSX.utils.aoa_to_sheet(wsData);
  ws1['!cols'] = [
    {wch:18},{wch:35},{wch:10},{wch:16},{wch:6},{wch:8},
    {wch:18},{wch:18},{wch:12},{wch:18},{wch:14},{wch:14},{wch:25}
  ];
  XLSX.utils.book_append_sheet(wb, ws1, 'Scope with Pricing');

  // --- Sheet 2: Cost Summary by CC ---
  const sumData = [
    ['Cost Summary by Cost Centre'],
    [],
    ['Cost Centre', 'Items Selected', 'Items Priced', 'Total EX GST', 'GST (10%)', 'Total INC GST']
  ];

  [...selectedCC].forEach(ccName => {
    const ccSel = itemSelections[ccName];
    if (!ccSel) return;
    const checked = Object.entries(ccSel).filter(([, v]) => v.checked);
    if (!checked.length) return;
    let ccTotal = 0, priced = 0;
    checked.forEach(([idx, v]) => {
      const pricing = itemPricing[ccName] && itemPricing[ccName][idx];
      const qty = parseFloat(v.qty) || 1;
      if (pricing && typeof pricing.price === 'number') {
        ccTotal += pricing.price * qty;
        priced++;
      }
    });
    sumData.push([ccName, checked.length, priced, ccTotal, ccTotal * 0.1, ccTotal * 1.1]);
  });
  sumData.push([]);
  sumData.push(['TOTAL', '', '', grandTotal, grandTotal * 0.1, grandTotal * 1.1]);

  const ws2 = XLSX.utils.aoa_to_sheet(sumData);
  ws2['!cols'] = [{wch:22},{wch:15},{wch:14},{wch:18},{wch:14},{wch:18}];
  XLSX.utils.book_append_sheet(wb, ws2, 'Cost Summary');

  const fileName = proj.name ? `${proj.name.replace(/[^a-z0-9]/gi, '_')}_pricing.xlsx` : 'scope_pricing.xlsx';
  XLSX.writeFile(wb, fileName);
}
```

---

## Step 5 — Add Cost Control Panel HTML to Step 4

Find this in the HTML (inside `id="step4"`):
```html
<div class="review-body" id="reviewBody"></div>
```

**Replace** it with:
```html
<div id="costControlPanel" class="cost-control-bar">
  <div class="cost-control-bar-top">
    <div>
      <div class="cost-total-label">Estimated Total (EX GST)</div>
      <div class="cost-total-value" id="ccGrandTotal">$0</div>
      <div class="cost-total-gst" id="ccGstTotal"></div>
    </div>
    <button class="btn btn-success" onclick="exportWithPricing()">📊 Export with Pricing</button>
  </div>
  <div class="cost-breakdown-grid" id="ccBreakdownGrid"></div>
  <div class="cost-unpriced-banner" id="ccUnpricedBanner"></div>
</div>
<div class="review-body" id="reviewBody"></div>
```

---

## Step 6 — Save project data includes pricing

Find the `saveCurrentProject` function. Inside it, where `itemSelections` is saved, also save `itemPricing`:

Find this in the function:
```javascript
itemSelections: itemSelections,
```

Add after it:
```javascript
itemPricing: itemPricing,
```

Then in `loadProject`, where `itemSelections` is loaded:
```javascript
itemSelections = project.itemSelections || {};
```

Add after:
```javascript
itemPricing = project.itemPricing || {};
```

---

## Summary of files to add/modify

| File | Action |
|------|--------|
| `price_data.js` | **ADD** to project folder (provided) |
| `index.html` | **MODIFY** — follow Steps 1–6 above |

That's it. The price_data.js contains all trade and product pricing from the Deep Dive Excel, pre-structured and ready to use.
