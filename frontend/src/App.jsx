import { useEffect, useMemo, useState } from 'react';
import { api } from './services/api';

const DEFAULT_TIER = 'Silver';

function formatCurrency(value) {
  const numeric = Number(value || 0);
  return `₹${numeric.toFixed(2)}`;
}

export default function App() {
  const [config, setConfig] = useState(null);
  const [selectedTier, setSelectedTier] = useState(DEFAULT_TIER);
  const [quantity, setQuantity] = useState(1);
  const [festivalOffer, setFestivalOffer] = useState(false);
  const [member, setMember] = useState(false);
  const [bill, setBill] = useState(null);
  const [loading, setLoading] = useState(true);
  const [pricingLoading, setPricingLoading] = useState(false);
  const [priceFile, setPriceFile] = useState(null);
  const [importReport, setImportReport] = useState(null);
  const [importLoading, setImportLoading] = useState(false);
  const [importError, setImportError] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    async function loadConfig() {
      try {
        const data = await api.getConfig();
        setConfig(data);
        if (data.tiers && data.tiers.length) {
          const firstAvailable = data.tiers.find((tier) => !tier.sold_out) || data.tiers[0];
          setSelectedTier(firstAvailable.name);
        }
      } catch (err) {
        setError(err.message || 'Unable to load show configuration.');
      } finally {
        setLoading(false);
      }
    }

    loadConfig();
  }, []);

  useEffect(() => {
    if (!config) return;

    const selected = config.tiers.find((tier) => tier.name === selectedTier);
    if (!selected || selected.sold_out) {
      setBill(null);
      return;
    }

    async function fetchBill() {
      setPricingLoading(true);
      setError('');
      setSuccess(false);

      try {
        const payload = {
          tier: selectedTier,
          quantity,
          festival_offer: festivalOffer,
          member,
        };

        const result = await api.priceBooking(payload);
        setBill(result);
      } catch (err) {
        setError(err.message || 'Unable to calculate price.');
        setBill(null);
      } finally {
        setPricingLoading(false);
      }
    }

    fetchBill();
  }, [config, selectedTier, quantity, festivalOffer, member]);

  const selectedTierInfo = useMemo(() => {
    if (!config) return null;
    return config.tiers.find((tier) => tier.name === selectedTier) || config.tiers[0];
  }, [config, selectedTier]);

  const handleDecrease = () => {
    if (!selectedTierInfo || selectedTierInfo.sold_out) return;
    setQuantity((current) => Math.max(1, Math.min(current - 1, selectedTierInfo.available_seats)));
  };

  const handleIncrease = () => {
    if (!selectedTierInfo || selectedTierInfo.sold_out) return;
    setQuantity((current) => Math.min(current + 1, selectedTierInfo.available_seats));
  };

  const handleConfirm = () => {
    if (!bill) return;
    setSuccess(true);
  };

  const handleImport = async (event) => {
    event.preventDefault();
    if (!priceFile) {
      setImportError('Choose a CSV file first.');
      return;
    }

    setImportLoading(true);
    setImportError('');
    try {
      const report = await api.importPrices(priceFile);
      const nextConfig = await api.getConfig();
      setConfig(nextConfig);
      setImportReport(report);
      const firstAvailable = nextConfig.tiers.find((tier) => !tier.sold_out) || nextConfig.tiers[0];
      setSelectedTier(firstAvailable?.name || DEFAULT_TIER);
      setQuantity(1);
      setPriceFile(null);
      event.target.reset();
    } catch (err) {
      setImportError(err.message || 'Unable to import the price list.');
    } finally {
      setImportLoading(false);
    }
  };

  const handleReset = async () => {
    setImportLoading(true);
    setImportError('');
    try {
      const nextConfig = await api.resetPrices();
      setConfig(nextConfig);
      setImportReport(null);
      setSelectedTier(nextConfig.tiers.find((tier) => !tier.sold_out)?.name || DEFAULT_TIER);
      setQuantity(1);
      setPriceFile(null);
    } catch (err) {
      setImportError(err.message || 'Unable to reset prices.');
    } finally {
      setImportLoading(false);
    }
  };

  if (loading) {
    return <div className="page-shell"><div className="panel loading-panel">Loading show details…</div></div>;
  }

  if (!config) {
    return <div className="page-shell"><div className="panel error-panel">{error || 'No show configuration available.'}</div></div>;
  }

  return (
    <div className="page-shell">
      <header className="topbar">
        <div>
          <div className="brand">CINEPRICE</div>
          <p className="sub-brand">Friday Night Booking</p>
        </div>
      </header>

      <main className="booking-layout">
        <section className="panel left-panel">
          <div className="movie-header">
            <div>
              <p className="eyebrow">Now showing</p>
              <h1>The Midnight Premiere</h1>
            </div>
            <div className="showtime">Friday • 8:30 PM</div>
          </div>

          <div className="section-title">Choose your seat tier</div>
          <div className="tier-grid">
            {config.tiers.map((tier) => {
              const isSelected = selectedTier === tier.name;
              const disabled = tier.sold_out;

              return (
                <button
                  key={tier.name}
                  type="button"
                  className={`tier-card ${isSelected ? 'selected' : ''} ${disabled ? 'sold-out' : ''}`}
                  onClick={() => !disabled && setSelectedTier(tier.name)}
                  disabled={disabled}
                >
                  <div className="tier-topline">
                    <span>{tier.name}</span>
                    {disabled && <span className="sold-tag">SOLD OUT</span>}
                  </div>
                  <div className="tier-price">{formatCurrency(tier.price)}</div>
                  <div className="tier-meta">{tier.available_seats} seats left</div>
                </button>
              );
            })}
          </div>

          <div className="section-title">Quantity</div>
          <div className="quantity-box">
            <button type="button" onClick={handleDecrease} aria-label="Decrease quantity">−</button>
            <span>{quantity}</span>
            <button type="button" onClick={handleIncrease} aria-label="Increase quantity">+</button>
          </div>

          <div className="section-title">Offers</div>
          <div className="toggle-list">
            <label className="toggle-row">
              <div>
                <span className="toggle-label">Festival Offer</span>
                <small>{formatCurrency(config.festival_discount)} flat discount</small>
              </div>
              <input type="checkbox" checked={festivalOffer} onChange={(e) => setFestivalOffer(e.target.checked)} />
            </label>

            <label className="toggle-row">
              <div>
                <span className="toggle-label">Member Discount</span>
                <small>{config.member_discount_percentage}% up to {formatCurrency(config.member_discount_cap)}</small>
              </div>
              <input type="checkbox" checked={member} onChange={(e) => setMember(e.target.checked)} />
            </label>
          </div>

          <div className="section-title">Import Price List</div>
          <form className="import-panel" onSubmit={handleImport}>
            <div className="import-controls">
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={(event) => setPriceFile(event.target.files?.[0] || null)}
              />
              <button type="submit" disabled={importLoading}>
                {importLoading ? 'Importing…' : 'Import CSV'}
              </button>
              <button type="button" className="reset-button" onClick={handleReset} disabled={importLoading}>
                Reset defaults
              </button>
            </div>
            {importError && <div className="import-error">{importError}</div>}
            {importReport && (
              <div className="import-report">
                <div className="import-counts" aria-label="Import summary">
                  <span className="import-count">Imported <strong>{importReport.summary.imported}</strong></span>
                  <span className="import-count">De-duplicated <strong>{importReport.summary.deduplicated}</strong></span>
                  <span className="import-count">Rejected <strong>{importReport.summary.rejected}</strong></span>
                </div>
                <div className="report-section">
                  <strong>Cleaned price list</strong>
                  {importReport.cleaned_prices.map((item) => (
                    <div key={item.seat_class} className="report-row">
                      <span>{item.seat_class}</span><span>{formatCurrency(item.price)}</span>
                    </div>
                  ))}
                </div>
                {importReport.deduplicated.length > 0 && (
                  <div className="report-section">
                    <strong>De-duplicated rows</strong>
                    {importReport.deduplicated.map((item) => (
                      <div key={`${item.row}-${item.seat_class}`} className="report-row">
                        <span>Row {item.row}: {item.seat_class}</span><span>{item.reason}</span>
                      </div>
                    ))}
                  </div>
                )}
                {importReport.rejected.length > 0 && (
                  <div className="report-section rejected-list">
                    <strong>Rejected rows</strong>
                    {importReport.rejected.map((item) => (
                      <div key={`${item.row}-${item.reason}`} className="report-row">
                        <span>{item.seat_class || `Row ${item.row}`}</span><span>{item.reason}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </form>

          {error && <div className="message error-message">{error}</div>}
        </section>

        <aside className="panel right-panel">
          <div className="summary-header">
            <div>
              <p className="eyebrow">Booking summary</p>
              <h2>Bill breakdown</h2>
            </div>
          </div>

          {pricingLoading ? (
            <div className="bill-loading">Calculating your totals…</div>
          ) : bill ? (
            <>
              <div className="summary-item">
                <span>{bill.tier}</span>
                <span>{quantity} x {formatCurrency(bill.unit_price)}</span>
              </div>

              <div className="bill-breakdown">
                <div className="line"><span>Tickets / Base subtotal</span><strong>{formatCurrency(bill.base_subtotal)}</strong></div>
                <div className="line deduction"><span>Festival discount</span><strong>-{formatCurrency(bill.festival_discount)}</strong></div>
                <div className="line deduction"><span>Member discount</span><strong>-{formatCurrency(bill.member_discount)}</strong></div>
                <div className="line"><span>Convenience fee</span><strong>{formatCurrency(bill.convenience_fee)}</strong></div>
                <div className="line"><span>Taxable subtotal</span><strong>{formatCurrency(bill.taxable_subtotal)}</strong></div>
                <div className="line"><span>GST ({bill.gst_rate}%)</span><strong>{formatCurrency(bill.gst)}</strong></div>
              </div>

              <div className="total-row">
                <span>Final payable</span>
                <strong>{formatCurrency(bill.total)}</strong>
              </div>

              <button type="button" className="confirm-button" onClick={handleConfirm}>Confirm Booking</button>

              {success && (
                <div className="success-box">
                  <h3>Booking priced successfully</h3>
                  <p>Amount payable {formatCurrency(bill.total)}</p>
                </div>
              )}
            </>
          ) : (
            <div className="bill-placeholder">Select a valid seat tier to view pricing.</div>
          )}
        </aside>
      </main>
    </div>
  );
}
