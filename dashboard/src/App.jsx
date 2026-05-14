import React, { useState, useEffect } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, BarChart, Bar, Cell
} from 'recharts';

const API_BASE = "http://localhost:8000";

function App() {
  const [status, setStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [gapDetected, setGapDetected] = useState(false);
  const [log, setLog] = useState([
    { time: "14:32:07", msg: "System initialized. Phase 11 Omega Brain engine active.", type: "info" },
    { time: "14:32:08", msg: "Regime detected. Adaptive weighting enabled for all assets.", type: "info" }
  ]);
  const [backtestDate, setBacktestDate] = useState("2026-05-10");
  const [backtesting, setBacktesting] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statusRes, historyRes] = await Promise.all([
          fetch(`${API_BASE}/status`),
          fetch(`${API_BASE}/history`)
        ]);
        const sData = await statusRes.json();
        setStatus(sData);
        setHistory(await historyRes.json());
        
        // Mock Gap Detection (for demo)
        if (sData.active_trades > 0 && !gapDetected) {
            setGapDetected(true);
        }

        setLoading(false);
      } catch (err) {
        console.error("API Error:", err);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [gapDetected]);

  const runBacktest = async () => {
    setBacktesting(true);
    try {
      const res = await fetch(`${API_BASE}/backtest/run?date=${backtestDate}`, { method: 'POST' });
      const data = await res.json();
      alert(`Backtest complete! Added ${data.trades_added} trades to history.`);
    } catch (err) {
      alert("Backtest failed: " + err.message);
    }
    setBacktesting(false);
  };

  if (loading) return (
    <div style={{ background: '#080b0f', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="dot" style={{ width: 20, height: 20 }}></div>
    </div>
  );

  const balance = status?.balance || 10000.0;
  const dayPnl = 338.42; // Placeholder for demo
  const openPnl = Object.values(status?.positions || {}).reduce((a, p) => a + (p.pnl || 0), 0);

  return (
    <div style={{ background: 'var(--bg0)', minHeight: '100vh' }}>
      {/* RECONNECT BANNER */}
      {gapDetected && (
        <div className="reconnect-banner">
          <span>⚡</span>
          <span>Laptop was offline. Detected <strong>{status?.active_trades} open trades</strong> that may have hit TP/SL during gap. Running gap-fill analysis...</span>
          <button className="reconnect-btn" onClick={() => setGapDetected(false)}>ANALYZE GAP</button>
        </div>
      )}

      {/* TOPBAR */}
      <div className="topbar">
        <div className="logo">ACE<span>/</span>TRADER <span style={{ color: 'var(--text2)', fontWeight: 300 }}>{status?.phase || "PHASE 11"}</span></div>
        <div className="topbar-center">
          <StatChip label="Balance" value={`$${balance.toLocaleString()}`} />
          <StatChip label="Today P&L" value={`+$${dayPnl.toFixed(2)} (+3.38%)`} className="pos" />
          <StatChip label="Open P&L" value={`$${openPnl >= 0 ? '+' : ''}${openPnl.toFixed(2)}`} className={openPnl >= 0 ? 'pos' : 'neg'} />
          <StatChip label="Win Rate" value="45.8%" />
          <StatChip label="Sharpe" value="2.40" className="pos" />
        </div>
        <div className="status-badge">
          <div className="dot"></div>
          <span>LIVE</span>
          <span style={{ color: 'var(--text2)', marginLeft: 8, fontSize: 10 }}>{new Date().toLocaleTimeString()}</span>
        </div>
      </div>

      <div className="main-layout">
        {/* ═══ LEFT COLUMN ═══ */}
        <div className="left-col">
          <div className="tabs">
            <Tab label="OVERVIEW" active={activeTab === 'overview'} onClick={() => setActiveTab('overview')} />
            <Tab label="POSITIONS" active={activeTab === 'positions'} onClick={() => setActiveTab('positions')} />
            <Tab label="HISTORY" active={activeTab === 'history'} onClick={() => setActiveTab('history')} />
            <Tab label="ANALYTICS" active={activeTab === 'analytics'} onClick={() => setActiveTab('analytics')} />
          </div>

          {activeTab === 'overview' && (
            <div className="tab-content active">
              <div className="section">
                <div className="section-title">Portfolio</div>
                <div className="portfolio-grid">
                  <PCard label="Total Equity" value={`$${balance.toLocaleString()}`} sub="+$338 today" sparkData={[10000, 10100, 10050, 10200, 10338]} color="var(--green)" />
                  <PCard label="Unrealised P&L" value={`$${openPnl >= 0 ? '+' : ''}${openPnl.toFixed(2)}`} sub={`${status?.active_trades} open positions`} color={openPnl >= 0 ? 'var(--green)' : 'var(--red)'} />
                  <PCard label="Realised Today" value="+$214.12" sub="11 trades closed" color="var(--green)" />
                  <PCard label="Max Drawdown" value="2.98%" sub="CB threshold: 3%" color="var(--amber)" />
                  <PCard label="Profit Factor" value="1.46" sub="Win: 45.8%" color="var(--green)" />
                </div>
              </div>

              <div className="section">
                <div className="section-title">Equity Curve</div>
                <div style={{ height: 180 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={history.map((t, i) => ({ n: i, v: 10000 + (t.pnl_val || 0) }))}>
                      <defs>
                        <linearGradient id="colorV" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--green)" stopOpacity={0.1}/>
                          <stop offset="95%" stopColor="var(--green)" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                      <XAxis hide />
                      <YAxis stroke="var(--text2)" fontSize={10} domain={['auto', 'auto']} />
                      <Tooltip contentStyle={{ background: 'var(--bg2)', border: 'none' }} />
                      <Area type="monotone" dataKey="v" stroke="var(--green)" fillOpacity={1} fill="url(#colorV)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="section">
                <div className="section-title">Open Positions</div>
                <table className="positions-table">
                  <thead>
                    <tr>
                      <th>Symbol</th><th>Side</th><th>Entry</th><th>Size</th><th>P&L</th><th>Strategy</th><th>Duration</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(status?.positions || {}).map(([sym, pos]) => (
                      <tr key={sym} onClick={() => setActiveTab('positions')} style={{ cursor: 'pointer' }}>
                        <td><div className="coin-cell">
                          <div className="coin-icon" style={{ color: '#f7931a' }}>{sym.split('/')[0].substring(0,3)}</div>
                          <div><div className="mono" style={{ fontWeight: 600 }}>{sym}</div></div>
                        </div></td>
                        <td><span className={`side-badge ${pos.side.toLowerCase()}`}>{pos.side}</span></td>
                        <td className="mono">${pos.entry_price.toLocaleString()}</td>
                        <td className="mono">{pos.qty}</td>
                        <td>
                          <div className={`mono ${pos.pnl >= 0 ? 'pos' : 'neg'}`}>
                            {pos.pnl >= 0 ? '+' : ''}${pos.pnl?.toFixed(2)}
                          </div>
                          <div className="pnl-bar-wrap">
                            <div className={`pnl-bar ${pos.pnl >= 0 ? 'pos' : 'neg'}`} style={{ width: '40%' }}></div>
                          </div>
                        </td>
                        <td><span className="tag">MOMENTUM</span></td>
                        <td className="mono" style={{ color: 'var(--text2)' }}>3h 18m</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'positions' && (
            <div className="tab-content active">
              <div className="section">
                <div className="section-title">Open Positions — Full Analysis</div>
                {Object.entries(status?.positions || {}).map(([sym, pos]) => (
                  <PositionCard key={sym} symbol={sym} pos={pos} />
                ))}
              </div>
            </div>
          )}

          {activeTab === 'history' && (
            <div className="tab-content active">
                <div className="section">
                    <div className="section-title">Trade History</div>
                    <div className="history-list">
                        {history.slice().reverse().map((t, i) => (
                            <HistoryItem key={i} trade={t} />
                        ))}
                    </div>
                </div>
            </div>
          )}

          {activeTab === 'analytics' && (
            <div className="tab-content active">
              <div className="section">
                <div className="section-title">Manual Historical Replay</div>
                <div className="card" style={{ display: 'flex', gap: '1rem', alignItems: 'center', padding: '1rem' }}>
                  <div className="stat-label">SELECT DATE (YYYY-MM-DD)</div>
                  <input 
                    type="date" 
                    value={backtestDate} 
                    onChange={(e) => setBacktestDate(e.target.value)}
                    style={{ background: 'var(--bg1)', border: '1px solid var(--border)', color: 'var(--text0)', padding: '6px 12px', borderRadius: '4px', fontFamily: 'var(--mono)' }}
                  />
                  <button 
                    className="reconnect-btn" 
                    onClick={runBacktest}
                    disabled={backtesting}
                    style={{ margin: 0, opacity: backtesting ? 0.5 : 1 }}
                  >
                    {backtesting ? "REPLAYING..." : "RUN REPLAY"}
                  </button>
                  <span style={{ fontSize: '10px', color: 'var(--text2)', fontFamily: 'var(--mono)' }}>
                    Replays Phase 9.5 logic for 24h on this date.
                  </span>
                </div>
              </div>

              <div className="section">
                <div className="section-title">Performance Analytics</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div className="card">
                    <div className="lbl">SHARPE RATIO</div>
                    <div className="big pos">2.40</div>
                  </div>
                  <div className="card">
                    <div className="lbl">WIN RATE</div>
                    <div className="big pos">45.8%</div>
                  </div>
                  <div className="card">
                    <div className="lbl">MAX DRAWDOWN</div>
                    <div className="big" style={{ color: 'var(--amber)' }}>2.98%</div>
                  </div>
                  <div className="card">
                    <div className="lbl">EXPECTANCY</div>
                    <div className="big pos">+$14.10</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ═══ RIGHT COLUMN ═══ */}
        <div className="right-col">
          <div className="regime-indicator">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--text2)', letterSpacing: 1 }}>MARKET REGIME</span>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 700, color: 'var(--green)' }}>BULL</span>
            </div>
            <div className="regime-bar">
              <div className="regime-seg" style={{ width: '60%', background: 'var(--green)', opacity: 0.7 }}></div>
              <div className="regime-seg" style={{ width: '25%', background: 'var(--amber)', opacity: 0.7 }}></div>
              <div className="regime-seg" style={{ width: '15%', background: 'var(--red)', opacity: 0.7 }}></div>
            </div>
          </div>

          <div className="indicator-grid">
            <Indicator label="EMA200 DEV" value="+3.2%" signal="↑ BULL" color="var(--green)" />
            <Indicator label="RSI (14)" value="58.4" signal="neutral" color="var(--amber)" />
            <Indicator label="ATR (14)" value="$1,240" signal="normal" color="var(--text2)" />
            <Indicator label="VOLUME" value="1.8×" signal="above avg" color="var(--green)" />
            <Indicator label="EMA9 / EMA21" value="↑ Cross" signal="bullish" color="var(--green)" />
            <Indicator label="CIRCUIT BRKR" value="ARMED" signal="DD: 0.8%" color="var(--green)" />
          </div>

          <div style={{ padding: 16, borderBottom: '1px solid var(--border)' }}>
            <div style={{ fontSize: 10, color: 'var(--purple)', fontFamily: 'var(--mono)', letterSpacing: 1, marginBottom: 10 }}>ML SIGNAL LAYER</div>
            <MLRow label="XGBoost score" value={0.75} color="var(--purple)" />
            <MLRow label="RF confidence" value={0.62} color="var(--purple)" />
            <MLRow label="Ensemble vote" value={0.50} color="var(--amber)" />
            <div className="reasoning-box">
              Phase 9: ML score neutralized at 0.5.<br/>
              Reason: rule-based only mode.<br/>
              Regime: BULL → long priority.<br/>
              Macro gate: BTC above EMA200.
            </div>
          </div>

          <div className="exec-log">
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 10, color: 'var(--text2)', fontFamily: 'var(--mono)' }}>EXECUTION LOG</span>
            </div>
            {log.map((entry, i) => (
              <div key={i} className="log-entry">
                <div className="log-time">{entry.time}</div>
                <div className={`log-msg ${entry.type}`}>{entry.msg}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Components
function StatChip({ label, value, className }) {
  return (
    <div className="stat-chip">
      <span className="label">{label}</span>
      <span className={`val ${className} mono`}>{value}</span>
    </div>
  );
}

function Tab({ label, active, onClick }) {
  return <div className={`tab ${active ? 'active' : ''}`} onClick={onClick}>{label}</div>;
}

function PCard({ label, value, sub, color, sparkData }) {
  return (
    <div className="p-card">
      <div className="lbl">{label}</div>
      <div className="big" style={{ color }}>{value}</div>
      <div className="sub">{sub}</div>
      {sparkData && (
        <div style={{ height: 32, marginTop: 4 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sparkData.map((v, i) => ({ v, i }))}>
              <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

function PositionCard({ symbol, pos }) {
  return (
    <div style={{ background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 8, marginBottom: 16, overflow: 'hidden' }}>
      <div style={{ padding: 14, background: 'var(--bg3)', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div className="coin-icon" style={{ width: 36, height: 36, color: '#f7931a' }}>{symbol.substring(0,3)}</div>
          <div><div style={{ fontWeight: 700, fontSize: 15 }}>{symbol}</div></div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className={`mono ${pos.pnl >= 0 ? 'pos' : 'neg'}`} style={{ fontSize: 20, fontWeight: 700 }}>
            {pos.pnl >= 0 ? '+' : ''}${pos.pnl?.toFixed(2)}
          </div>
        </div>
      </div>
      <div style={{ padding: 16, display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
        <div className="metrics-grid">
           <div className="m-item"><div className="k">ENTRY</div><div className="v neu mono">${pos.entry_price.toLocaleString()}</div></div>
           <div className="m-item"><div className="k">SIZE</div><div className="v neu mono">{pos.qty}</div></div>
           <div className="m-item"><div className="k">TAKE PROFIT</div><div className="v pos mono">${pos.tp?.toLocaleString()}</div></div>
           <div className="m-item"><div className="k">STOP LOSS</div><div className="v neg mono">${pos.sl?.toLocaleString()}</div></div>
        </div>
        <div className="strat-panel">
          <div className="strat-title">DECISION LOGIC</div>
          <div className="decision-tree">
            <div className="dt-node pass"><span className="dt-icon">✓</span> Regime: BULL</div>
            <div className="dt-node pass"><span className="dt-icon">✓</span> EMA9/21 Cross</div>
            <div className="dt-node info"><span className="dt-icon">→</span> Conf: 0.65</div>
          </div>
        </div>
        <div className="ml-panel">
            <div className="ml-title">EXECUTION REASONING</div>
            <div className="reasoning-box">{pos.thinking?.reason || "Rules-based entry on EMA crossover confirmed by BTC macro regime."}</div>
        </div>
      </div>
    </div>
  );
}

function HistoryItem({ trade }) {
  const isWin = trade.pnl_pct > 0;
  return (
    <div className={`hist-item ${isWin ? 'win' : 'loss'}`}>
      <div className="hist-row1">
        <div style={{ display: 'flex', gap: 10 }}>
          <span className="hist-symbol">{trade.symbol}</span>
          <span className={`side-badge ${trade.side.toLowerCase()}`}>{trade.side}</span>
        </div>
        <div className={`hist-pnl ${isWin ? 'pos' : 'neg'}`}>
          {isWin ? '+' : ''}${trade.pnl_val?.toFixed(2)}
        </div>
      </div>
      <div className="hist-row2">
        <span className="tag">{new Date(trade.closed_at).toLocaleString()}</span>
        <span className="tag">Exit: {trade.reason}</span>
      </div>
    </div>
  );
}

function Indicator({ label, value, signal, color }) {
  return (
    <div className="ind-card">
      <div className="ind-name">{label}</div>
      <div className="ind-val" style={{ color }}>{value}</div>
      <div className="ind-signal" style={{ color }}>{signal}</div>
    </div>
  );
}

function MLRow({ label, value, color }) {
  return (
    <div className="ml-row">
      <span className="key">{label}</span>
      <div className="ml-bar-wrap"><div className="ml-bar" style={{ width: `${value * 100}%`, background: color }}></div></div>
      <span className="ml-score" style={{ color }}>{value.toFixed(2)}</span>
    </div>
  );
}

export default App;
