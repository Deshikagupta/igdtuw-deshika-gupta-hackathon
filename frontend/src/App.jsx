import { useCallback, useEffect, useState } from "react";
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, BarChart3,
  BriefcaseBusiness, CheckCircle2, ChevronRight, CircleDollarSign,
  FileSearch, LayoutDashboard, LoaderCircle, Plus, RefreshCw,
  ShieldAlert, Sparkles, Trash2, TrendingDown, X
} from "lucide-react";
import {
  Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis, BarChart, Bar
} from "recharts";
import "./App.css";

const ASSET_TYPES = [
  "Equity", "Corporate Bond", "Government Bond", "Corporate Loan", "Derivative"
];
const SOURCES = [
  { value: "financial_news", label: "Financial news" },
  { value: "social_media", label: "Social media" }
];
const COLORS = ["#7c8cff", "#45c4a0", "#f5b85d", "#ed7d9a", "#9c83e6"];
const money = (n) => new Intl.NumberFormat("en-US", {
  style: "currency", currency: "USD", maximumFractionDigits: 0
}).format(Number(n || 0));
const pct = (n) => `${(Number(n || 0) * 100).toFixed(1)}%`;
const pretty = (s) => String(s || "Unknown").replaceAll("_", " ");
const sentimentColor = (n) => n > 0.08 ? "positive" : n < -0.08 ? "negative" : "neutral";

async function request(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers }
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = body.detail;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail || body));
  }
  return body;
}

function Metric({ label, value, note, icon: Icon, tone = "" }) {
  return <article className="metric card">
    <div className={`metric-icon ${tone}`}><Icon size={19} /></div>
    <span className="muted metric-label">{label}</span>
    <strong className="metric-value">{value}</strong>
    <span className="metric-note">{note}</span>
  </article>;
}

function Empty({ icon: Icon = Activity, title, detail }) {
  return <div className="empty"><Icon size={26} /><strong>{title}</strong><span>{detail}</span></div>;
}

export default function App() {
  const [page, setPage] = useState("Overview");
  const [portfolio, setPortfolio] = useState({ summary: { total_value: 0, asset_count: 0, allocation: [] }, assets: [] });
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [stress, setStress] = useState(null);
  const [text, setText] = useState("");
  const [company, setCompany] = useState("");
  const [ticker, setTicker] = useState("");
  const [source, setSource] = useState("financial_news");
  const [runAutomaticStress, setRunAutomaticStress] = useState(true);
  const [stressMode, setStressMode] = useState("scenario");
  const [scenarioKey, setScenarioKey] = useState("equity_downturn");
  const [shocks, setShocks] = useState({
    Equity: -20, "Corporate Bond": -10, "Government Bond": 3,
    "Corporate Loan": -12, Derivative: -25
  });
  const [showAdd, setShowAdd] = useState(false);
  const [assetForm, setAssetForm] = useState({
    asset_id: "", asset_name: "", asset_type: "Equity", ticker: "",
    sector: "", quantity: "100", current_price: "100"
  });

  const refresh = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    setError("");
    try {
      const [p, h] = await Promise.all([
        request("/api/portfolio"),
        request("/health").catch(() => null)
      ]);
      setPortfolio(p);
      setHealth(h);
    } catch (e) {
      setError(`Could not load portfolio: ${e.message}. Check that the FastAPI server is running on port 8000.`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  async function runAction(fn, successMessage) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await fn();
      if (successMessage) setNotice(successMessage);
    } catch (e) {
      setError(e.message || "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function addAsset(e) {
    e.preventDefault();
    await runAction(async () => {
      const payload = {
        ...assetForm,
        quantity: Number(assetForm.quantity),
        current_price: Number(assetForm.current_price),
        ticker: assetForm.ticker.trim() || null,
        sector: assetForm.sector.trim() || null
      };
      await request("/api/portfolio", { method: "POST", body: JSON.stringify(payload) });
      setShowAdd(false);
      setAssetForm({ asset_id: "", asset_name: "", asset_type: "Equity", ticker: "", sector: "", quantity: "100", current_price: "100" });
      await refresh(true);
    }, "Asset added to your portfolio.");
  }

  async function deleteAsset(asset) {
    if (!window.confirm(`Remove ${asset.asset_name} from the portfolio?`)) return;
    await runAction(async () => {
      await request(`/api/portfolio/${encodeURIComponent(asset.asset_id)}`, { method: "DELETE" });
      await refresh(true);
    }, "Asset removed.");
  }

  async function analyzeText(e) {
    e.preventDefault();
    await runAction(async () => {
      const result = await request("/api/analyze", {
        method: "POST",
        body: JSON.stringify({
          text: text.trim(), company: company.trim() || null,
          ticker: ticker.trim() || null, source, persist: true,
          run_stress_test: runAutomaticStress
        })
      });
      setAnalysis(result);
      if (result.stress_test) setStress(result.stress_test);
      setPage("Analysis");
    });
  }

  async function runStress(e) {
    e.preventDefault();
    await runAction(async () => {
      const payload = stressMode === "scenario"
        ? { scenario_key: scenarioKey }
        : { custom_shocks_pct: shocks };
      const result = await request("/api/stress-test", {
        method: "POST", body: JSON.stringify(payload)
      });
      setStress(result);
    });
  }

  const summary = portfolio.summary || {};
  const assets = portfolio.assets || [];
  const allocation = summary.allocation || [];
  const signal = analysis?.signal;
  const stressResults = stress?.asset_level_results || [];
  const sidebar = [
    { name: "Overview", icon: LayoutDashboard },
    { name: "Portfolio", icon: BriefcaseBusiness },
    { name: "Analysis", icon: FileSearch },
    { name: "Stress Testing", icon: ShieldAlert }
  ];

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark"><Activity size={23} /></div>
        <div><strong>RiskLens</strong><span>INTELLIGENCE PLATFORM</span></div>
      </div>
      <div className="workspace-label">WORKSPACE</div>
      <nav>
        {sidebar.map(({ name, icon: Icon }) =>
          <button key={name} className={`nav-item ${page === name ? "active" : ""}`} onClick={() => setPage(name)}>
            <Icon size={18} /><span>{name}</span>{page === name && <ChevronRight size={16} className="nav-arrow" />}
          </button>
        )}
      </nav>
      <div className="sidebar-bottom">
        <div className="system-status"><span className={`status-dot ${health ? "online" : ""}`} />
          <div><strong>API connection</strong><span>{health ? "Service responding" : "Not verified"}</span></div>
        </div>
        <div className="prototype-note">HACKATHON PROTOTYPE<br />Illustrative risk intelligence</div>
      </div>
    </aside>

    <main className="main">
      <header className="topbar">
        <div><div className="eyebrow">RISK INTELLIGENCE / 2026</div><h1>{page}</h1></div>
        <div className="top-actions">
          <span className="live-label"><span className="status-dot online" /> Connected workspace</span>
          <button className="icon-button" title="Refresh data" onClick={() => refresh()}><RefreshCw size={17} /></button>
          <div className="avatar">DG</div>
        </div>
      </header>

      {error && <div className="alert error"><AlertTriangle size={18} /><span>{error}</span><button onClick={() => setError("")}><X size={16} /></button></div>}
      {notice && <div className="alert success"><CheckCircle2 size={18} /><span>{notice}</span><button onClick={() => setNotice("")}><X size={16} /></button></div>}
      {loading && <div className="loading-line"><LoaderCircle className="spin" size={17} /> Loading live portfolio data…</div>}

      {page === "Overview" && <>
        <section className="welcome-row">
          <div><h2>Market risk, made actionable.</h2><p>Monitor portfolio exposure, interpret financial events, and explore illustrative downside scenarios.</p></div>
          <button className="primary" onClick={() => setPage("Analysis")}><Sparkles size={17} /> Analyze an event</button>
        </section>
        <section className="metrics-grid">
          <Metric label="PORTFOLIO VALUE" value={money(summary.total_value)} note="Current recorded market value" icon={CircleDollarSign} tone="purple" />
          <Metric label="ASSETS TRACKED" value={summary.asset_count ?? assets.length} note="Across portfolio asset classes" icon={BriefcaseBusiness} tone="blue" />
          <Metric label="LATEST IMPACT SCORE" value={signal ? `${signal.impact_score}/10` : "—"} note={signal ? pretty(signal.risk_level) : "Run an analysis to generate a signal"} icon={Activity} tone="orange" />
          <Metric label="LATEST STRESS LOSS" value={stress ? money(stress.absolute_loss) : "—"} note={stress ? `${Number(stress.percentage_loss).toFixed(2)}% portfolio impact` : "Run a scenario to evaluate exposure"} icon={TrendingDown} tone="red" />
        </section>
        <section className="dashboard-grid">
          <article className="card panel allocation-panel">
            <div className="panel-heading"><div><h3>Portfolio allocation</h3><p>Exposure by asset class</p></div><span className="subtle-tag">LIVE DATA</span></div>
            {allocation.length ? <div className="allocation-content">
              <div className="donut-wrap"><ResponsiveContainer width="100%" height={225}>
                <PieChart><Pie data={allocation} dataKey="market_value" nameKey="asset_type" innerRadius={63} outerRadius={88} paddingAngle={3} stroke="none">
                  {allocation.map((item, i) => <Cell key={item.asset_type} fill={COLORS[i % COLORS.length]} />)}
                </Pie><Tooltip formatter={(v) => money(v)} /></PieChart>
              </ResponsiveContainer><div className="donut-center"><strong>{money(summary.total_value)}</strong><span>Total value</span></div></div>
              <div className="legend">{allocation.map((item, i) => <div className="legend-row" key={item.asset_type}>
                <span className="legend-dot" style={{ background: COLORS[i % COLORS.length] }} />
                <span className="legend-name">{item.asset_type}</span><strong>{pct(item.weight)}</strong>
              </div>)}</div>
            </div> : <Empty icon={BarChart3} title="No allocation data yet" detail="Add portfolio assets to see exposure by asset class." />}
          </article>
          <article className="card panel exposure-panel">
            <div className="panel-heading"><div><h3>Exposure breakdown</h3><p>Value held by asset type</p></div></div>
            {allocation.length ? <ResponsiveContainer width="100%" height={255}>
              <BarChart data={allocation} layout="vertical" margin={{ left: 8, right: 18, top: 8, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#252c3b" horizontal={false} />
                <XAxis type="number" tickFormatter={(v) => `$${Number(v) >= 1000000 ? `${(v / 1000000).toFixed(1)}m` : `${Math.round(v / 1000)}k`}`} stroke="#798397" fontSize={11} />
                <YAxis type="category" dataKey="asset_type" width={115} stroke="#9aa4b6" fontSize={10} />
                <Tooltip formatter={(v) => money(v)} contentStyle={{ background: "#171d2a", border: "1px solid #30394b", borderRadius: 10 }} />
                <Bar dataKey="market_value" name="Market value" radius={[0, 5, 5, 0]}>{allocation.map((item, i) => <Cell key={item.asset_type} fill={COLORS[i % COLORS.length]} />)}</Bar>
              </BarChart>
            </ResponsiveContainer> : <Empty icon={BarChart3} title="Exposure appears here" detail="Your allocation chart will update from the API." />}
          </article>
        </section>
        <section className="card panel table-panel">
          <div className="panel-heading"><div><h3>Portfolio holdings</h3><p>Your tracked assets and current valuations</p></div>
            <button className="secondary" onClick={() => { setShowAdd(true); setPage("Portfolio"); }}><Plus size={16} /> Add asset</button>
          </div>
          <AssetTable assets={assets} onDelete={deleteAsset} />
        </section>
        <Disclaimer />
      </>}

      {page === "Portfolio" && <>
        <section className="welcome-row"><div><h2>Portfolio management</h2><p>Manage holdings and inspect the allocation calculated by the backend.</p></div>
          <button className="primary" onClick={() => setShowAdd(true)}><Plus size={17} /> Add asset</button>
        </section>
        <section className="metrics-grid two">
          <Metric label="TOTAL MARKET VALUE" value={money(summary.total_value)} note="Quantity × current price" icon={CircleDollarSign} tone="purple" />
          <Metric label="HOLDINGS" value={assets.length} note="Assets in the current portfolio" icon={BriefcaseBusiness} tone="blue" />
        </section>
        {showAdd && <section className="card panel form-panel">
          <div className="panel-heading"><div><h3>Add a holding</h3><p>Values are synthetic USD inputs for this prototype.</p></div><button className="icon-button" onClick={() => setShowAdd(false)}><X size={18} /></button></div>
          <form className="asset-form" onSubmit={addAsset}>
            <label>Asset ID<input required maxLength="50" value={assetForm.asset_id} onChange={e => setAssetForm({ ...assetForm, asset_id: e.target.value })} placeholder="e.g. ASSET-001" /></label>
            <label>Asset name<input required maxLength="150" value={assetForm.asset_name} onChange={e => setAssetForm({ ...assetForm, asset_name: e.target.value })} placeholder="e.g. Example Corp. shares" /></label>
            <label>Asset type<select value={assetForm.asset_type} onChange={e => setAssetForm({ ...assetForm, asset_type: e.target.value })}>{ASSET_TYPES.map(t => <option key={t}>{t}</option>)}</select></label>
            <label>Ticker<input value={assetForm.ticker} onChange={e => setAssetForm({ ...assetForm, ticker: e.target.value })} placeholder="Optional" /></label>
            <label>Sector<input value={assetForm.sector} onChange={e => setAssetForm({ ...assetForm, sector: e.target.value })} placeholder="Optional" /></label>
            <label>Quantity<input required min="0.0001" type="number" step="any" value={assetForm.quantity} onChange={e => setAssetForm({ ...assetForm, quantity: e.target.value })} /></label>
            <label>Current price (USD)<input required min="0" type="number" step="any" value={assetForm.current_price} onChange={e => setAssetForm({ ...assetForm, current_price: e.target.value })} /></label>
            <div className="form-actions"><button type="button" className="secondary" onClick={() => setShowAdd(false)}>Cancel</button><button disabled={busy} className="primary" type="submit">{busy ? "Saving…" : "Save asset"}</button></div>
          </form>
        </section>}
        <section className="card panel table-panel"><div className="panel-heading"><div><h3>All holdings</h3><p>{assets.length} assets · updated from the portfolio API</p></div></div><AssetTable assets={assets} onDelete={deleteAsset} /></section>
        <Disclaimer />
      </>}

      {page === "Analysis" && <>
        <section className="welcome-row"><div><h2>Turn unstructured news into risk signals.</h2><p>Submit a financial event to classify its risk, estimate its impact, and optionally evaluate portfolio stress.</p></div></section>
        <section className="analysis-grid">
          <article className="card panel">
            <div className="panel-heading"><div><h3>Event intelligence</h3><p>Risk engine input</p></div><span className="subtle-tag"><Sparkles size={12} /> NLP ANALYSIS</span></div>
            <form className="analysis-form" onSubmit={analyzeText}>
              <label>Financial text <span className="muted">Required · up to 10,000 characters</span>
                <textarea required minLength="1" maxLength="10000" rows="7" value={text} onChange={e => setText(e.target.value)} placeholder="Paste a financial headline or event report…&#10;&#10;Example: A major manufacturer reported a sharp decline in quarterly revenue and lowered its annual outlook amid weaker demand." />
              </label>
              <div className="form-two">
                <label>Company<input maxLength="120" value={company} onChange={e => setCompany(e.target.value)} placeholder="Optional company name" /></label>
                <label>Ticker<input value={ticker} onChange={e => setTicker(e.target.value)} placeholder="Optional ticker" /></label>
              </div>
              <label>Source<select value={source} onChange={e => setSource(e.target.value)}>{SOURCES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}</select></label>
              <label className="check-row"><input type="checkbox" checked={runAutomaticStress} onChange={e => setRunAutomaticStress(e.target.checked)} /><span><strong>Evaluate automatic stress trigger</strong><small>Run a stress test if the resulting signal meets trigger conditions.</small></span></label>
              <button className="primary full" disabled={busy || !text.trim()} type="submit">{busy ? <><LoaderCircle className="spin" size={17} /> Analyzing…</> : <><Sparkles size={17} /> Generate risk signal</>}</button>
            </form>
          </article>
          <article className="card panel result-panel">
            <div className="panel-heading"><div><h3>Signal assessment</h3><p>Model output from your API</p></div></div>
            {signal ? <div className="signal-result">
              <div className="score-top"><span className="muted">MARKET IMPACT SCORE</span><strong className={`impact-score ${signal.impact_score >= 7 ? "negative" : ""}`}>{signal.impact_score}<small>/10</small></strong></div>
              <div className="impact-meter"><span style={{ width: `${signal.impact_score * 10}%` }} /></div>
              <div className="result-badges"><span className={`pill ${String(signal.risk_level).toLowerCase()}`}>{pretty(signal.risk_level)} risk</span><span className={`pill ${sentimentColor(signal.sentiment_score)}`}>{pretty(signal.sentiment_label)}</span></div>
              <div className="result-fields">
                <ResultField label="Event classification" value={signal.event_type} />
                <ResultField label="Sentiment score" value={`${Number(signal.sentiment_score).toFixed(3)} (−1 to +1)`} />
                <ResultField label="Event confidence" value={pct(signal.event_confidence)} />
                <ResultField label="Overall confidence" value={pct(signal.confidence)} />
                <ResultField label="Company" value={signal.company || "Not specified"} />
                <ResultField label="Signal ID" value={signal.signal_id} />
              </div>
              {signal.matched_keywords?.length > 0 && <div className="keywords"><span className="muted">Matched keywords</span><div>{signal.matched_keywords.map(k => <span key={k}>{k}</span>)}</div></div>}
              {analysis.trigger && <div className={`trigger-box ${analysis.trigger.triggered ? "triggered" : ""}`}><strong>{analysis.trigger.triggered ? "Stress trigger activated" : "No stress trigger"}</strong><p>{analysis.trigger.reason}</p></div>}
              {analysis.stress_test && <button className="secondary full" onClick={() => { setStress(analysis.stress_test); setPage("Stress Testing"); }}>View generated stress test <ChevronRight size={16} /></button>}
            </div> : <Empty icon={FileSearch} title="Awaiting your first signal" detail="Submit financial text to see classification, sentiment, confidence and impact." />}
          </article>
        </section>
        {signal && <section className="card panel source-panel"><div className="panel-heading"><div><h3>Analyzed source text</h3><p>{signal.source} · {signal.timestamp ? new Date(signal.timestamp).toLocaleString() : "Timestamp unavailable"}</p></div></div><p className="source-quote">{signal.text}</p></section>}
        <Disclaimer />
      </>}

      {page === "Stress Testing" && <>
        <section className="welcome-row"><div><h2>Test portfolio resilience.</h2><p>Apply configured scenarios or define custom percentage shocks by asset class.</p></div></section>
        <section className="stress-layout">
          <article className="card panel">
            <div className="panel-heading"><div><h3>Scenario configuration</h3><p>Choose a stress-test mode</p></div><ShieldAlert size={19} className="muted" /></div>
            <form className="analysis-form" onSubmit={runStress}>
              <div className="mode-picker">
                <button type="button" className={stressMode === "scenario" ? "mode-card selected" : "mode-card"} onClick={() => setStressMode("scenario")}><TrendingDown size={20} /><strong>Preset scenario</strong><span>Use a configured scenario key</span></button>
                <button type="button" className={stressMode === "custom" ? "mode-card selected" : "mode-card"} onClick={() => setStressMode("custom")}><Activity size={20} /><strong>Custom shocks</strong><span>Set shocks for each asset class</span></button>
              </div>
              {stressMode === "scenario" ? <label>Scenario key<input required value={scenarioKey} onChange={e => setScenarioKey(e.target.value)} pattern="[a-z0-9_-]+" placeholder="e.g. equity_downturn" /><small>Use a scenario key configured by your backend. Example: equity_downturn.</small></label> :
                <div className="shock-fields">{ASSET_TYPES.map(type => <label key={type}>{type} <span className="muted">(%)</span><input type="number" min="-100" max="100" step="any" value={shocks[type]} onChange={e => setShocks({ ...shocks, [type]: Number(e.target.value) })} /></label>)}</div>}
              <button className="primary full" type="submit" disabled={busy}>{busy ? <><LoaderCircle className="spin" size={17} /> Running…</> : <><Activity size={17} /> Run stress test</>}</button>
            </form>
          </article>
          <article className="card panel"><div className="panel-heading"><div><h3>Latest scenario</h3><p>Most recent stress-test result</p></div><span className="subtle-tag">ILLUSTRATIVE</span></div>
            {stress ? <div className="stress-result">
              <div className="stress-loss"><span className="muted">ESTIMATED PORTFOLIO LOSS</span><strong>{money(stress.absolute_loss)}</strong><span className="loss-pct"><ArrowDownRight size={15} /> {Number(stress.percentage_loss).toFixed(2)}% under scenario</span></div>
              <div className="stress-values"><div><span>Before shock</span><strong>{money(stress.portfolio_before)}</strong></div><div><span>After shock</span><strong>{money(stress.portfolio_after)}</strong></div></div>
              <div className="scenario-meta"><span>Scenario</span><strong>{pretty(stress.scenario_name || stress.scenario_key)}</strong><span>Mode</span><strong>{pretty(stress.mode)}</strong><span>Test ID</span><strong className="mono">{stress.stress_test_id}</strong></div>
              <p className="assumptions">{stress.assumptions_note || "Shocks are simplified illustrative assumptions; results are not a market forecast."}</p>
            </div> : <Empty icon={ShieldAlert} title="No stress test yet" detail="Choose a preset or custom shocks and run the test." />}
          </article>
        </section>
        {stress && <>
          <section className="card panel table-panel"><div className="panel-heading"><div><h3>Asset-level impact</h3><p>How each holding responds to the selected shock</p></div></div>
            {stressResults.length ? <div className="table-wrap"><table><thead><tr><th>Asset</th><th>Type</th><th>Before</th><th>Shock</th><th>After</th><th>Change</th></tr></thead><tbody>{stressResults.map(a => <tr key={a.asset_id}><td><strong>{a.asset_name}</strong><small>{a.ticker || a.asset_id}</small></td><td>{a.asset_type}</td><td>{money(a.value_before)}</td><td className={a.shock_pct < 0 ? "negative" : "positive"}>{Number(a.shock_pct).toFixed(2)}%</td><td>{money(a.value_after)}</td><td className={a.absolute_loss > 0 ? "negative" : "positive"}>{money(a.value_after - a.value_before)}</td></tr>)}</tbody></table></div> : <Empty title="No asset-level results" detail="Add assets to the portfolio and rerun the scenario." />}
          </section>
          {stressResults.length > 0 && <section className="card panel"><div className="panel-heading"><div><h3>Impact by holding</h3><p>Value after scenario versus value before</p></div></div>
            <ResponsiveContainer width="100%" height={270}><BarChart data={stressResults} margin={{ top: 12, right: 20, left: 10, bottom: 50 }}><CartesianGrid strokeDasharray="3 3" stroke="#252c3b" /><XAxis dataKey="asset_name" tick={{ fill: "#a4adbd", fontSize: 10 }} angle={-20} textAnchor="end" interval={0} /><YAxis tickFormatter={v => `$${Math.round(v / 1000)}k`} tick={{ fill: "#8993a7", fontSize: 10 }} /><Tooltip formatter={v => money(v)} contentStyle={{ background: "#171d2a", border: "1px solid #30394b", borderRadius: 10 }} /><Bar dataKey="value_before" name="Before" fill="#7c8cff" radius={[4,4,0,0]} /><Bar dataKey="value_after" name="After" fill="#45c4a0" radius={[4,4,0,0]} /></BarChart></ResponsiveContainer>
          </section>}
        </>}
        <Disclaimer />
      </>}

      <footer className="footer"><span>RiskLens · Risk Intelligence Platform</span><span>Prototype only · Not investment advice</span></footer>
    </main>
    {busy && <div className="busy-indicator"><LoaderCircle size={15} className="spin" /> Processing request</div>}
  </div>;
}

function ResultField({ label, value }) {
  return <div className="result-field"><span>{label}</span><strong>{value ?? "—"}</strong></div>;
}

function AssetTable({ assets, onDelete }) {
  if (!assets?.length) return <Empty icon={BriefcaseBusiness} title="Your portfolio is empty" detail="Add a holding to begin monitoring asset allocation and stress exposure." />;
  return <div className="table-wrap"><table><thead><tr><th>Asset</th><th>Type</th><th>Sector</th><th>Quantity</th><th>Price</th><th>Market value</th><th>Weight</th><th /></tr></thead><tbody>
    {assets.map(a => <tr key={a.asset_id}><td><strong>{a.asset_name}</strong><small>{a.ticker || a.asset_id}</small></td><td><span className="type-chip">{a.asset_type}</span></td><td>{a.sector || "—"}</td><td>{Number(a.quantity).toLocaleString()}</td><td>{money(a.current_price)}</td><td><strong>{money(a.market_value)}</strong></td><td>{pct(a.weight)}</td><td><button className="delete-button" title={`Delete ${a.asset_name}`} onClick={() => onDelete(a)}><Trash2 size={15} /></button></td></tr>)}
  </tbody></table></div>;
}

function Disclaimer() {
  return <div className="disclaimer"><AlertTriangle size={15} /><span><strong>Prototype disclaimer:</strong> Values, event scores and scenario shocks are illustrative. Stress tests are simplified assumptions, not predictions or investment advice.</span></div>;
}
