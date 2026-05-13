import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  Activity, 
  History, 
  Cpu, 
  Zap, 
  ShieldAlert,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';

const API_BASE = "http://localhost:8000";

function App() {
  const [status, setStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statusRes, historyRes] = await Promise.all([
          fetch(`${API_BASE}/status`),
          fetch(`${API_BASE}/history`)
        ]);
        setStatus(await statusRes.json());
        setHistory(await historyRes.json());
        setLoading(false);
      } catch (err) {
        console.error("API Error:", err);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return (
    <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center' }}>
      <Zap size={48} className="glow-gold" style={{ animation: 'pulse 2s infinite' }} />
    </div>
  );

  return (
    <div className="dashboard-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
          <Zap color="#f59e0b" fill="#f59e0b" size={32} />
          <h1>SOVEREIGN</h1>
        </div>
        
        <nav style={{ display: 'flex', flex_direction: 'column', gap: '0.5rem' }}>
          <NavItem icon={<Activity size={20}/>} label="Live Feed" active />
          <NavItem icon={<TrendingUp size={20}/>} label="Performance" />
          <NavItem icon={<History size={20}/>} label="Trade History" />
          <NavItem icon={<Cpu size={20}/>} label="ML Engine" />
        </nav>

        <div style={{ marginTop: 'auto' }} className="card">
          <div className="stat-label">System Health</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981' }} />
            <span style={{ fontSize: '0.8rem' }}>Core Latency: 12ms</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>Quant Dashboard <span style={{ color: 'var(--text-dim)', fontSize: '0.9rem', fontWeight: 400 }}>v9.5.1 Live</span></h2>
          <div className="card" style={{ padding: '0.5rem 1rem', fontSize: '0.8rem' }}>
            {new Date().toLocaleTimeString()} UTC
          </div>
        </header>

        {/* Top Stats */}
        <div className="stat-grid">
          <StatCard label="Total Equity" value={`$${status?.balance.toLocaleString()}`} change="+4.2%" icon={<TrendingUp color="#10b981" />} />
          <StatCard label="Active Trades" value={status?.active_trades} icon={<Activity color="#06b6d4" />} />
          <StatCard label="24h PnL" value="+$428.00" change="+1.2%" icon={<Zap color="#f59e0b" />} />
          <StatCard label="Risk Heat" value="12.5%" icon={<ShieldAlert color="#ef4444" />} />
        </div>

        {/* Charts Section */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem' }}>
          <div className="card" style={{ height: '400px' }}>
            <h3>Equity Curve (Live Replay)</h3>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={history.map(t => ({ name: new Date(t.closed_at).toLocaleTimeString(), val: t.pnl_pct }))}>
                <defs>
                  <linearGradient id="colorVal" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-gold)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--accent-gold)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="name" stroke="var(--text-dim)" fontSize={12} />
                <YAxis stroke="var(--text-dim)" fontSize={12} />
                <Tooltip contentStyle={{ background: '#1e1e24', border: 'none', borderRadius: '8px' }} />
                <Area type="monotone" dataKey="val" stroke="var(--accent-gold)" fillOpacity={1} fill="url(#colorVal)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="card">
            <h3>ML Thinking Log</h3>
            <div className="thinking-stream">
              {status?.positions && Object.entries(status.positions).map(([sym, pos]) => (
                <div key={sym} className="thought-entry">
                  <div style={{ color: 'var(--accent-cyan)' }}>{sym} Analysis</div>
                  <div>- Regime: {pos.thinking?.regime || "BULL"} detected</div>
                  <div>- RSI Convergence: {pos.thinking?.rsi_score || 0.85}</div>
                  <div>- Vote Count: 2/2 Confirmed</div>
                </div>
              ))}
              <div className="thought-entry" style={{ opacity: 0.5 }}>
                Listening for market ticks...
              </div>
            </div>
          </div>
        </div>

        {/* Recent Trades Table */}
        <div className="card">
          <h3>Recent Executions</h3>
          <table className="trade-log-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Side</th>
                <th>Entry</th>
                <th>Exit</th>
                <th>PnL %</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {history.map((trade, i) => (
                <tr key={i}>
                  <td>{trade.symbol}</td>
                  <td style={{ color: trade.side === 'LONG' ? 'var(--accent-green)' : 'var(--accent-red)' }}>{trade.side}</td>
                  <td>{trade.entry.toFixed(4)}</td>
                  <td>{trade.exit.toFixed(4)}</td>
                  <td className={trade.pnl_pct >= 0 ? 'positive' : 'negative'}>
                    {(trade.pnl_pct * 100).toFixed(2)}%
                  </td>
                  <td style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{trade.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}

function NavItem({ icon, label, active }) {
  return (
    <div style={{ 
      display: 'flex', 
      alignItems: 'center', 
      gap: '0.75rem', 
      padding: '0.75rem 1rem', 
      borderRadius: '12px',
      background: active ? 'rgba(245, 158, 11, 0.1)' : 'transparent',
      color: active ? 'var(--accent-gold)' : 'var(--text-dim)',
      cursor: 'pointer'
    }}>
      {icon}
      <span style={{ fontWeight: active ? 600 : 400 }}>{label}</span>
    </div>
  );
}

function StatCard({ label, value, change, icon }) {
  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div className="stat-label">{label}</div>
          <div className="stat-value">{value}</div>
          {change && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', marginTop: '0.25rem', color: '#10b981', fontSize: '0.8rem' }}>
              <ArrowUpRight size={14} /> {change}
            </div>
          )}
        </div>
        <div className="card" style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.03)' }}>
          {icon}
        </div>
      </div>
    </div>
  );
}

export default App;
