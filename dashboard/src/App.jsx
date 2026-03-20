import React, { useState, useEffect, useMemo } from 'react';
import { collection, query, orderBy, limit, onSnapshot, doc, updateDoc, getDoc, setDoc } from 'firebase/firestore';
import { db } from './firebase';
import { LineChart, Line, BarChart, Bar, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, ComposedChart } from 'recharts';
import {
  Activity, TrendingUp, TrendingDown, DollarSign, ShieldAlert, Zap, BarChart3, Clock,
  LayoutGrid, Settings, Bell, FileText, Brain, Briefcase, ListOrdered, Shield,
  LineChart as LineChartIcon, AlertTriangle, Power, Pause, Play, Square, X,
  ChevronDown, Search, Eye, EyeOff, Wifi, WifiOff, Volume2, VolumeX,
  Download, Upload, RefreshCw, Target, Crosshair, Flame, Skull, CircleDot
} from 'lucide-react';

// ─── CONSTANTS ──────────────────────────────────────────────
const INR_RATE = 84.5;
const COLORS = { green: '#00d4aa', red: '#ff4757', blue: '#3b82f6', purple: '#8b5cf6', yellow: '#fbbf24', orange: '#f97316' };
const PIE_COLORS = [COLORS.green, COLORS.blue, COLORS.purple, COLORS.yellow, COLORS.orange, COLORS.red];

const ALL_STRATEGIES = [
  'MTF', 'STAT_ARB', 'MEAN_REVERSION', 'BREAKOUT', 'OBIS', 'VWAP_REVERSION',
  'LIQUIDITY_SWEEP', 'MTF_MACD', 'RSI_DIV', 'FIBONACCI', 'ICHIMOKU', 'ATR_EXPANSION',
  'VOLUME_PROFILE', 'PIVOT_POINTS', 'PSAR', 'SUPERTREND', 'GANN_FAN', 'HARMONIC',
  'LIQUIDITY_GRAB', 'TREND_EXHAUST'
];

// ─── SIDEBAR NAV ITEMS ──────────────────────────────────────
const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutGrid, section: 'OVERVIEW' },
  { id: 'trading', label: 'Trading', icon: LineChartIcon, section: 'OVERVIEW' },
  { id: 'strategies', label: 'Strategies', icon: Brain, section: 'ENGINE' },
  { id: 'portfolio', label: 'Portfolio', icon: Briefcase, section: 'ENGINE' },
  { id: 'orders', label: 'Orders', icon: ListOrdered, section: 'ENGINE' },
  { id: 'risk', label: 'Risk Mgmt', icon: Shield, section: 'CONTROLS' },
  { id: 'analytics', label: 'Analytics', icon: BarChart3, section: 'CONTROLS' },
  { id: 'alerts', label: 'Alerts', icon: Bell, section: 'CONTROLS' },
  { id: 'logs', label: 'Logs', icon: FileText, section: 'SYSTEM' },
  { id: 'settings', label: 'Settings', icon: Settings, section: 'SYSTEM' },
];

// ─── BINANCE PUBLIC API ─────────────────────────────────────
const BINANCE_API = 'https://api.binance.com/api/v3';
const TF_MAP = {'1m':'1m','5m':'5m','15m':'15m','1h':'1h','4h':'4h','1D':'1d','1W':'1w'};

async function fetchBinanceCandles(symbol='BTCUSDT', interval='1h', limit=100) {
  try {
    const res = await fetch(`${BINANCE_API}/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`);
    const data = await res.json();
    return data.map(d => ({
      time: new Date(d[0]).toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit'}),
      open: parseFloat(d[1]), high: parseFloat(d[2]), low: parseFloat(d[3]),
      close: parseFloat(d[4]), volume: parseFloat(d[5])
    }));
  } catch(e) { console.error('Binance fetch error:', e); return []; }
}

async function fetchBinancePrice(symbol='BTCUSDT') {
  try {
    const res = await fetch(`${BINANCE_API}/ticker/24hr?symbol=${symbol}`);
    const d = await res.json();
    return { price: parseFloat(d.lastPrice), change: parseFloat(d.priceChangePercent) };
  } catch(e) { return { price: 0, change: 0 }; }
}

// ─── RSI CALCULATOR ─────────────────────────────────────────
function calcRSI(closes, period=14) {
  const rsi = [];
  for (let i = 0; i < period; i++) rsi.push(50);
  let avgGain=0, avgLoss=0;
  for (let i=1; i<=period; i++) {
    const diff = closes[i]-closes[i-1];
    if(diff>0) avgGain+=diff; else avgLoss+=Math.abs(diff);
  }
  avgGain/=period; avgLoss/=period;
  rsi.push(avgLoss===0?100:100-(100/(1+avgGain/avgLoss)));
  for (let i=period+1; i<closes.length; i++) {
    const diff=closes[i]-closes[i-1];
    avgGain=(avgGain*(period-1)+(diff>0?diff:0))/period;
    avgLoss=(avgLoss*(period-1)+(diff<0?Math.abs(diff):0))/period;
    rsi.push(avgLoss===0?100:100-(100/(1+avgGain/avgLoss)));
  }
  return rsi;
}

// ─── HELPER COMPONENTS ──────────────────────────────────────
const StatusDot = ({status}) => {
  const colors = { running: 'bg-green-400', paused: 'bg-yellow-400', error: 'bg-red-400', offline: 'bg-gray-500' };
  return <div className={`w-2 h-2 rounded-full ${colors[status] || colors.offline} ${status === 'running' ? 'animate-pulse-glow' : ''}`} />;
};

const ConfirmModal = ({show, onConfirm, onCancel, title, message}) => {
  if (!show) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="card p-6 w-[400px] space-y-4 animate-slide-up">
        <div className="flex items-center gap-3">
          <AlertTriangle className="text-yellow-400" size={20} />
          <h3 className="text-lg font-bold">{title}</h3>
        </div>
        <p className="text-sm" style={{color:'var(--text-secondary)'}}>{message}</p>
        <div className="flex gap-3 justify-end pt-2">
          <button className="btn-ghost" onClick={onCancel}>Cancel</button>
          <button className="btn-danger" onClick={onConfirm}>Confirm Switch</button>
        </div>
      </div>
    </div>
  );
};

// ─── PANEL: DASHBOARD ───────────────────────────────────────
function DashboardPanel({ equity, trades, signals, balances, currentCapital, botStatus, useTestnet }) {
  const closedTrades = trades.filter(t => t.pnl !== undefined);
  const winRate = closedTrades.length > 0 ? (closedTrades.filter(t => t.pnl > 0).length / closedTrades.length) * 100 : 0;
  const totalPnl = closedTrades.reduce((s, t) => s + (t.pnl || 0), 0);
  const activePositions = trades.filter(t => t.pnl === undefined);

  const stats = [
    { label: 'Portfolio Value', value: `$${currentCapital.toFixed(2)}`, sub: `≈ ₹${(currentCapital*INR_RATE).toLocaleString('en-IN')}`, color: COLORS.green },
    { label: '24h PnL', value: `${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}`, sub: `${totalPnl >= 0 ? '+' : ''}${((totalPnl/currentCapital)*100).toFixed(2)}%`, color: totalPnl >= 0 ? COLORS.green : COLORS.red },
    { label: 'Win Rate', value: `${winRate.toFixed(1)}%`, sub: `${closedTrades.length} closed trades`, color: COLORS.blue },
    { label: 'Active Positions', value: activePositions.length, sub: `${trades.length} total`, color: COLORS.purple },
  ];

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s, i) => (
          <div key={i} className="card p-5 group">
            <p className="stat-label mb-2">{s.label}</p>
            <p className="text-2xl font-bold mono" style={{color: s.color}}>{s.value}</p>
            <p className="text-xs mt-1" style={{color:'var(--text-muted)'}}>{s.sub}</p>
          </div>
        ))}
      </div>

      {/* Equity + Signals Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold flex items-center gap-2"><TrendingUp size={14} style={{color:'var(--accent)'}}/> Equity Curve</h3>
            <span className="badge badge-green">LIVE</span>
          </div>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equity}>
                <defs>
                  <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={COLORS.green} stopOpacity={0.3}/>
                    <stop offset="95%" stopColor={COLORS.green} stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,43,61,0.5)" />
                <XAxis dataKey="time" tick={{fontSize:10, fill:'#4a5a70'}} axisLine={false} />
                <YAxis tick={{fontSize:10, fill:'#4a5a70'}} axisLine={false} domain={['auto','auto']} />
                <Tooltip contentStyle={{background:'#111820', border:'1px solid #1e2b3d', borderRadius:8, fontSize:12}} />
                <Area type="monotone" dataKey="value" stroke={COLORS.green} fill="url(#eqGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recent Signals */}
        <div className="card p-5">
          <h3 className="text-sm font-bold flex items-center gap-2 mb-4"><Zap size={14} style={{color:'var(--accent)'}}/> Live Signals</h3>
          <div className="space-y-2 max-h-[250px] overflow-y-auto">
            {signals.length === 0 ? (
              <p className="text-xs text-center py-8" style={{color:'var(--text-muted)'}}>Awaiting signals...</p>
            ) : signals.map((sig, i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-lg" style={{background:'var(--bg-tertiary)'}}>
                <div className={`w-1 h-8 rounded-full`} style={{background: sig.direction === 'LONG' ? COLORS.green : COLORS.red}} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold">{sig.symbol}</p>
                  <p className="text-[11px] truncate" style={{color:'var(--text-muted)'}}>{sig.direction} • {sig.reason || 'Signal detected'}</p>
                </div>
                <span className={`badge ${sig.direction === 'LONG' ? 'badge-green' : 'badge-red'}`}>{sig.direction}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bot Status + Assets */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-5">
          <h3 className="text-sm font-bold flex items-center gap-2 mb-4"><Activity size={14} style={{color:'var(--accent)'}}/> Bot Status</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center"><span className="text-xs" style={{color:'var(--text-secondary)'}}>Engine</span><div className="flex items-center gap-2"><StatusDot status={botStatus}/><span className="text-xs font-bold capitalize">{botStatus}</span></div></div>
            <div className="flex justify-between items-center"><span className="text-xs" style={{color:'var(--text-secondary)'}}>Mode</span><span className={useTestnet ? 'mode-badge-paper' : 'mode-badge-live'}>{useTestnet ? 'PAPER' : 'LIVE'}</span></div>
            <div className="flex justify-between items-center"><span className="text-xs" style={{color:'var(--text-secondary)'}}>Active Algos</span><span className="text-xs font-bold" style={{color:'var(--accent)'}}>20 / 20</span></div>
            <div className="flex justify-between items-center"><span className="text-xs" style={{color:'var(--text-secondary)'}}>Cycle</span><span className="text-xs font-bold">5m interval</span></div>
          </div>
        </div>

        <div className="card p-5">
          <h3 className="text-sm font-bold flex items-center gap-2 mb-4"><DollarSign size={14} style={{color:'var(--accent)'}}/> Assets</h3>
          <div className="space-y-2 max-h-[150px] overflow-y-auto">
            {balances.length === 0 ? (
              <p className="text-xs text-center py-4" style={{color:'var(--text-muted)'}}>Syncing...</p>
            ) : balances.map((b, i) => (
              <div key={i} className="flex justify-between items-center py-1.5">
                <span className="text-sm font-bold">{b.asset}</span>
                <div className="text-right">
                  <span className="text-sm mono font-bold">{b.balance?.toFixed(4)}</span>
                  <span className="text-[10px] ml-2" style={{color:'var(--text-muted)'}}>≈ ₹{(b.balance * INR_RATE).toLocaleString('en-IN')}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── PANEL: TRADING (REAL BINANCE DATA) ─────────────────────
function TradingPanel() {
  const [timeframe, setTimeframe] = useState('1h');
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [candles, setCandles] = useState([]);
  const [ticker, setTicker] = useState({price:0, change:0});
  const [loading, setLoading] = useState(true);
  const tfs = ['1m','5m','15m','1h','4h','1D','1W'];
  const symbols = ['BTCUSDT','ETHUSDT'];

  useEffect(() => {
    let active = true;
    const load = async () => {
      setLoading(true);
      const [c, t] = await Promise.all([
        fetchBinanceCandles(symbol, TF_MAP[timeframe], 100),
        fetchBinancePrice(symbol)
      ]);
      if (active) { setCandles(c); setTicker(t); setLoading(false); }
    };
    load();
    const interval = setInterval(load, 30000); // refresh every 30s
    return () => { active=false; clearInterval(interval); };
  }, [symbol, timeframe]);

  const rsiData = useMemo(() => {
    if(candles.length < 15) return [];
    const closes = candles.map(c=>c.close);
    const rsi = calcRSI(closes);
    return candles.map((c,i) => ({time:c.time, rsi: Math.round(rsi[i]*100)/100}));
  }, [candles]);

  const macdData = useMemo(() => {
    if(candles.length < 26) return [];
    const closes = candles.map(c=>c.close);
    const ema = (data,p) => { let e=[data[0]]; const k=2/(p+1); for(let i=1;i<data.length;i++) e.push(data[i]*k+e[i-1]*(1-k)); return e; };
    const e12=ema(closes,12), e26=ema(closes,26);
    return candles.map((c,i)=>({time:c.time, macd: Math.round((e12[i]-e26[i])*100)/100}));
  }, [candles]);

  const displaySymbol = symbol === 'BTCUSDT' ? 'BTC/USDT' : 'ETH/USDT';

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <select className="input w-36" value={symbol} onChange={e=>setSymbol(e.target.value)}>
            {symbols.map(s=><option key={s} value={s}>{s.replace('USDT','/USDT')}</option>)}
          </select>
          <span className="text-lg font-bold mono" style={{color: ticker.change >= 0 ? COLORS.green : COLORS.red}}>${ticker.price.toLocaleString()}</span>
          <span className={`badge ${ticker.change >= 0 ? 'badge-green' : 'badge-red'}`}>{ticker.change >= 0 ? '+' : ''}{ticker.change.toFixed(2)}%</span>
        </div>
        <div className="flex gap-1">
          {tfs.map(tf => (
            <button key={tf} className={`tab ${timeframe === tf ? 'active' : ''}`} onClick={() => setTimeframe(tf)}>{tf}</button>
          ))}
        </div>
      </div>

      <div className="card p-4">
        {loading ? <div className="h-[400px] flex items-center justify-center" style={{color:'var(--text-muted)'}}>Loading {displaySymbol} data from Binance...</div> : (
        <div className="h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={candles}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,43,61,0.4)" />
              <XAxis dataKey="time" tick={{fontSize:9, fill:'#4a5a70'}} axisLine={false} interval={Math.floor(candles.length/10)} />
              <YAxis domain={['auto','auto']} tick={{fontSize:10, fill:'#4a5a70'}} axisLine={false} />
              <Tooltip contentStyle={{background:'#111820', border:'1px solid #1e2b3d', borderRadius:8, fontSize:11}} />
              <Bar dataKey="volume" fill="rgba(0,212,170,0.15)" yAxisId="right" />
              <Line type="monotone" dataKey="close" stroke={COLORS.green} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="high" stroke="rgba(0,212,170,0.3)" strokeWidth={1} dot={false} strokeDasharray="2 2" />
              <Line type="monotone" dataKey="low" stroke="rgba(255,71,87,0.3)" strokeWidth={1} dot={false} strokeDasharray="2 2" />
              <YAxis yAxisId="right" orientation="right" tick={{fontSize:9, fill:'#4a5a70'}} axisLine={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>)}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-4">
          <p className="stat-label mb-2">RSI (14) — Live</p>
          <div className="h-[100px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={rsiData}>
                <Line type="monotone" dataKey="rsi" stroke={COLORS.purple} strokeWidth={1.5} dot={false} />
                <YAxis domain={[0,100]} tick={{fontSize:9, fill:'#4a5a70'}} axisLine={false} />
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,43,61,0.3)" />
                <Tooltip contentStyle={{background:'#111820', border:'1px solid #1e2b3d', borderRadius:8, fontSize:11}} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card p-4">
          <p className="stat-label mb-2">MACD — Live</p>
          <div className="h-[100px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={macdData}>
                <Bar dataKey="macd">{macdData.map((d,i) => <Cell key={i} fill={d.macd >= 0 ? COLORS.green : COLORS.red} />)}</Bar>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,43,61,0.3)" />
                <Tooltip contentStyle={{background:'#111820', border:'1px solid #1e2b3d', borderRadius:8, fontSize:11}} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── PANEL: STRATEGIES (REAL DATA) ──────────────────────────
function StrategyPanel({ signals, trades }) {
  const [selected, setSelected] = useState('MTF');
  const regimes = { MTF:'TRENDING', STAT_ARB:'MEAN_REVERTING', MEAN_REVERSION:'MEAN_REVERTING', BREAKOUT:'BREAKOUT', OBIS:'HIGH_VOL', VWAP_REVERSION:'MEAN_REVERTING', LIQUIDITY_SWEEP:'BREAKOUT', MTF_MACD:'TRENDING', RSI_DIV:'MEAN_REVERTING', FIBONACCI:'TRENDING', ICHIMOKU:'TRENDING', ATR_EXPANSION:'BREAKOUT', VOLUME_PROFILE:'MEAN_REVERTING', PIVOT_POINTS:'MEAN_REVERTING', PSAR:'TRENDING', SUPERTREND:'TRENDING', GANN_FAN:'TRENDING', HARMONIC:'MEAN_REVERTING', LIQUIDITY_GRAB:'BREAKOUT', TREND_EXHAUST:'MEAN_REVERTING' };

  // Derive per-strategy stats from Firebase signals
  const stratStats = useMemo(() => {
    const stats = {};
    ALL_STRATEGIES.forEach(s => {
      const sSignals = signals.filter(sig => (sig.strategy || '').toUpperCase().includes(s.replace('_','')));
      const sTrades = trades.filter(t => (t.strategy || '').toUpperCase().includes(s.replace('_','')));
      const wins = sTrades.filter(t => t.pnl > 0).length;
      const total = sTrades.length;
      const pnl = sTrades.reduce((sum, t) => sum + (t.pnl || 0), 0);
      stats[s] = { signals: sSignals.length, trades: total, winRate: total > 0 ? Math.round(wins/total*100) : 0, pnl: Math.round(pnl*100)/100 };
    });
    return stats;
  }, [signals, trades]);

  const sel = stratStats[selected] || { signals:0, trades:0, winRate:0, pnl:0 };
  const totalSignals = signals.length;

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold flex items-center gap-2"><Brain size={18} style={{color:'var(--accent)'}}/> Strategy Engine</h2>
        <span className="badge badge-green">20 Active • {totalSignals} signals</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card p-4 max-h-[500px] overflow-y-auto">
          <p className="stat-label mb-3">All Strategies</p>
          <div className="space-y-1">
            {ALL_STRATEGIES.map(s => (
              <div key={s} className={`flex items-center justify-between p-2.5 rounded-lg cursor-pointer transition-all ${selected === s ? 'bg-[rgba(0,212,170,0.1)]' : ''}`}
                style={{borderLeft: selected === s ? '3px solid var(--accent)' : '3px solid transparent'}}
                onClick={() => setSelected(s)}>
                <span className="text-sm font-medium">{s}</span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] mono" style={{color:'var(--text-muted)'}}>{stratStats[s]?.signals || 0}s</span>
                  <StatusDot status="running" />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-2 space-y-4">
          <div className="card p-5">
            <h3 className="text-lg font-bold mb-1">{selected}</h3>
            <p className="text-xs mb-4" style={{color:'var(--text-muted)'}}>Regime Gate: {regimes[selected] || 'TRENDING'} • Tier: INTRADAY</p>
            <div className="grid grid-cols-3 gap-4">
              <div><p className="stat-label">Signals</p><p className="text-xl font-bold mono" style={{color:COLORS.green}}>{sel.signals}</p></div>
              <div><p className="stat-label">Win Rate</p><p className="text-xl font-bold mono" style={{color:COLORS.blue}}>{sel.winRate}%</p></div>
              <div><p className="stat-label">PnL</p><p className="text-xl font-bold mono" style={{color: sel.pnl >= 0 ? COLORS.green : COLORS.red}}>{sel.pnl >= 0 ? '+' : ''}${sel.pnl}</p></div>
            </div>
          </div>

          <div className="card p-5">
            <p className="stat-label mb-3">Recent Signals for {selected}</p>
            <div className="space-y-2 max-h-[200px] overflow-y-auto">
              {signals.filter(s => (s.strategy || '').toUpperCase().includes(selected.replace('_',''))).slice(0,5).map((sig,i) => (
                <div key={i} className="flex items-center justify-between p-2 rounded" style={{background:'var(--bg-tertiary)'}}>
                  <div className="flex items-center gap-2">
                    <span className={`badge ${sig.direction === 'LONG' ? 'badge-green' : 'badge-red'}`}>{sig.direction}</span>
                    <span className="text-sm">{sig.symbol}</span>
                  </div>
                  <span className="text-[10px] mono" style={{color:'var(--text-muted)'}}>{sig.timestamp ? new Date(sig.timestamp).toLocaleTimeString() : ''}</span>
                </div>
              ))}
              {signals.filter(s => (s.strategy || '').toUpperCase().includes(selected.replace('_',''))).length === 0 && (
                <p className="text-xs text-center py-4" style={{color:'var(--text-muted)'}}>No signals yet for {selected}</p>
              )}
            </div>
          </div>

          <div className="card p-5">
            <p className="stat-label mb-3">Parameters</p>
            <div className="space-y-3">
              {['EMA Fast (9)', 'EMA Slow (21)', 'RSI Length (14)', 'ATR Mult (1.5)'].map((p,i) => (
                <div key={i} className="flex items-center justify-between">
                  <span className="text-xs" style={{color:'var(--text-secondary)'}}>{p}</span>
                  <input className="input w-20 text-center text-xs" defaultValue={p.match(/\((\S+)\)/)?.[1]} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── PANEL: PORTFOLIO ───────────────────────────────────────
function PortfolioPanel({ trades, balances }) {
  const openPositions = trades.filter(t => t.pnl === undefined);
  const closedTrades = trades.filter(t => t.pnl !== undefined);
  const pieData = balances.length > 0 ? balances.map(b => ({name: b.asset, value: b.balance * INR_RATE})) : [{name:'USDT', value:1000}];

  return (
    <div className="space-y-4 animate-slide-up">
      <h2 className="text-lg font-bold flex items-center gap-2"><Briefcase size={18} style={{color:'var(--accent)'}}/> Portfolio</h2>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Allocation */}
        <div className="card p-5">
          <p className="stat-label mb-3">Asset Allocation</p>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" stroke="none">
                  {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{background:'#111820', border:'1px solid #1e2b3d', borderRadius:8, fontSize:11}} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="space-y-1 mt-2">
            {pieData.map((d,i) => (
              <div key={i} className="flex items-center gap-2 text-xs"><div className="w-2.5 h-2.5 rounded-sm" style={{background: PIE_COLORS[i%PIE_COLORS.length]}}/><span>{d.name}</span></div>
            ))}
          </div>
        </div>

        {/* Open Positions */}
        <div className="lg:col-span-2 card overflow-hidden">
          <div className="p-4 border-b" style={{borderColor:'var(--border)'}}><p className="stat-label">Open Positions ({openPositions.length})</p></div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr><th className="table-header">Symbol</th><th className="table-header">Side</th><th className="table-header">Entry</th><th className="table-header">Size</th><th className="table-header">Strategy</th></tr></thead>
              <tbody>
                {openPositions.length === 0 ? (
                  <tr><td colSpan="5" className="table-cell text-center" style={{color:'var(--text-muted)'}}>No open positions</td></tr>
                ) : openPositions.map((t, i) => (
                  <tr key={i} className="table-row">
                    <td className="table-cell font-bold">{t.symbol}</td>
                    <td className="table-cell"><span className={`badge ${t.direction === 'LONG' ? 'badge-green' : 'badge-red'}`}>{t.direction}</span></td>
                    <td className="table-cell mono">{t.entry?.toFixed(2)}</td>
                    <td className="table-cell mono">{t.qty}</td>
                    <td className="table-cell text-xs" style={{color:'var(--text-muted)'}}>{t.strategy || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Closed Trades */}
      <div className="card overflow-hidden">
        <div className="p-4 border-b" style={{borderColor:'var(--border)'}}><p className="stat-label">Closed Trades ({closedTrades.length})</p></div>
        <div className="overflow-x-auto max-h-[300px] overflow-y-auto">
          <table className="w-full">
            <thead><tr><th className="table-header">Symbol</th><th className="table-header">Side</th><th className="table-header">Entry</th><th className="table-header">Exit</th><th className="table-header">PnL</th></tr></thead>
            <tbody>
              {closedTrades.length === 0 ? (
                <tr><td colSpan="5" className="table-cell text-center" style={{color:'var(--text-muted)'}}>No closed trades yet</td></tr>
              ) : closedTrades.map((t, i) => (
                <tr key={i} className="table-row">
                  <td className="table-cell font-bold">{t.symbol}</td>
                  <td className="table-cell"><span className={`badge ${t.direction === 'LONG' ? 'badge-green' : 'badge-red'}`}>{t.direction}</span></td>
                  <td className="table-cell mono">{t.entry?.toFixed(2)}</td>
                  <td className="table-cell mono">{t.exit?.toFixed(2) || '—'}</td>
                  <td className="table-cell font-bold mono" style={{color: t.pnl >= 0 ? COLORS.green : COLORS.red}}>{t.pnl >= 0 ? '+' : ''}{t.pnl?.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── PANEL: ORDERS ──────────────────────────────────────────
function OrdersPanel() {
  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold flex items-center gap-2"><ListOrdered size={18} style={{color:'var(--accent)'}}/> Order Management</h2>
        <button className="kill-switch flex items-center gap-2"><Skull size={14}/> KILL ALL</button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-5">
          <p className="stat-label mb-3">Pending Orders</p>
          <div className="text-center py-12" style={{color:'var(--text-muted)'}}>
            <ListOrdered size={32} className="mx-auto mb-2 opacity-30" />
            <p className="text-xs">No pending orders in queue</p>
          </div>
        </div>

        <div className="card p-5">
          <p className="stat-label mb-3">Quick Order (Manual Override)</p>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <button className="btn-primary py-3 font-bold">BUY / LONG</button>
              <button className="btn-danger py-3 font-bold">SELL / SHORT</button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div><label className="stat-label">Symbol</label><input className="input mt-1" defaultValue="BTC/USDT" /></div>
              <div><label className="stat-label">Amount ($)</label><input className="input mt-1" defaultValue="100" /></div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div><label className="stat-label">Stop Loss</label><input className="input mt-1" placeholder="Auto" /></div>
              <div><label className="stat-label">Take Profit</label><input className="input mt-1" placeholder="Auto" /></div>
            </div>
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="p-4 border-b" style={{borderColor:'var(--border)'}}><p className="stat-label">Order History</p></div>
        <div className="text-center py-12" style={{color:'var(--text-muted)'}}>
          <p className="text-xs">Order history will appear here as trades execute</p>
        </div>
      </div>
    </div>
  );
}

// ─── PANEL: RISK ────────────────────────────────────────────
function RiskPanel() {
  const [maxDD, setMaxDD] = useState(3);
  const [riskPer, setRiskPer] = useState(1);
  const [dailyLoss, setDailyLoss] = useState(35);

  return (
    <div className="space-y-4 animate-slide-up">
      <h2 className="text-lg font-bold flex items-center gap-2"><Shield size={18} style={{color:'var(--accent)'}}/> Risk Management</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card p-5">
          <p className="stat-label mb-2">Max Drawdown</p>
          <p className="text-2xl font-bold mono" style={{color:COLORS.red}}>{maxDD}%</p>
          <input type="range" min="1" max="10" value={maxDD} onChange={e=>setMaxDD(e.target.value)} className="w-full mt-2 accent-red-500" />
        </div>
        <div className="card p-5">
          <p className="stat-label mb-2">Per-Trade Risk</p>
          <p className="text-2xl font-bold mono" style={{color:COLORS.yellow}}>{riskPer}%</p>
          <input type="range" min="0.5" max="5" step="0.5" value={riskPer} onChange={e=>setRiskPer(e.target.value)} className="w-full mt-2 accent-yellow-500" />
        </div>
        <div className="card p-5">
          <p className="stat-label mb-2">Daily Loss Used</p>
          <p className="text-2xl font-bold mono" style={{color: dailyLoss > 70 ? COLORS.red : COLORS.green}}>{dailyLoss}%</p>
          <div className="progress-bar mt-2"><div className="progress-fill" style={{width:`${dailyLoss}%`, background: dailyLoss > 70 ? COLORS.red : COLORS.green}}/></div>
        </div>
        <div className="card p-5">
          <p className="stat-label mb-2">Risk Score</p>
          <p className="text-2xl font-bold mono" style={{color:COLORS.green}}>LOW</p>
          <p className="text-xs mt-1" style={{color:'var(--text-muted)'}}>Portfolio heat: 2.1%</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-5">
          <p className="stat-label mb-3">Risk Rules</p>
          <div className="space-y-3">
            {[{label:'Max Portfolio Heat', val:'6%', active:true}, {label:'Single Asset Cap', val:'40%', active:true}, {label:'Daily Loss Stop', val:'3%', active:true}, {label:'Max Open Positions', val:'5', active:true}, {label:'Correlation Limit', val:'0.85', active:false}].map((r,i)=>(
              <div key={i} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${r.active ? 'bg-green-400' : 'bg-gray-500'}`}/>
                  <span className="text-sm">{r.label}</span>
                </div>
                <span className="text-sm font-bold mono">{r.val}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card p-5">
          <p className="stat-label mb-3">Exposure Breakdown</p>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs mb-1"><span>Long Exposure</span><span className="font-bold" style={{color:COLORS.green}}>60%</span></div>
              <div className="progress-bar"><div className="progress-fill" style={{width:'60%', background:COLORS.green}}/></div>
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1"><span>Short Exposure</span><span className="font-bold" style={{color:COLORS.red}}>20%</span></div>
              <div className="progress-bar"><div className="progress-fill" style={{width:'20%', background:COLORS.red}}/></div>
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1"><span>Cash</span><span className="font-bold" style={{color:COLORS.blue}}>20%</span></div>
              <div className="progress-bar"><div className="progress-fill" style={{width:'20%', background:COLORS.blue}}/></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── PANEL: ANALYTICS (REAL DATA) ───────────────────────────
function AnalyticsPanel({ equity, trades }) {
  const closedTrades = trades.filter(t => t.pnl !== undefined);
  const totalPnl = closedTrades.reduce((s,t) => s+(t.pnl||0), 0);
  const wins = closedTrades.filter(t => t.pnl > 0);
  const losses = closedTrades.filter(t => t.pnl < 0);
  const avgWin = wins.length > 0 ? wins.reduce((s,t)=>s+t.pnl,0)/wins.length : 0;
  const avgLoss = losses.length > 0 ? Math.abs(losses.reduce((s,t)=>s+t.pnl,0)/losses.length) : 0;

  // Derived metrics
  const sharpe = equity.length > 2 ? (() => {
    const returns = equity.slice(1).map((e,i) => (e.value - equity[i].value)/equity[i].value);
    const mean = returns.reduce((s,r)=>s+r,0)/returns.length;
    const std = Math.sqrt(returns.reduce((s,r)=>s+(r-mean)**2,0)/returns.length);
    return std > 0 ? (mean/std * Math.sqrt(252)).toFixed(2) : '0.00';
  })() : '—';

  const maxDD = equity.length > 1 ? (() => {
    let peak = equity[0].value, maxDd = 0;
    equity.forEach(e => { if(e.value > peak) peak = e.value; const dd = (peak - e.value)/peak*100; if(dd > maxDd) maxDd = dd; });
    return maxDd.toFixed(1);
  })() : '0.0';

  const expectancy = closedTrades.length > 0 ? (totalPnl / closedTrades.length).toFixed(2) : '0.00';

  return (
    <div className="space-y-4 animate-slide-up">
      <h2 className="text-lg font-bold flex items-center gap-2"><BarChart3 size={18} style={{color:'var(--accent)'}}/> Performance Analytics</h2>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[{l:'Sharpe Ratio', v:sharpe, c:COLORS.green}, {l:'Avg Win', v: avgWin > 0 ? `+$${avgWin.toFixed(2)}` : '$0', c:COLORS.blue}, {l:'Max Drawdown', v:`-${maxDD}%`, c:COLORS.red}, {l:'Expectancy', v:`${expectancy >= 0 ? '+' : ''}$${expectancy}`, c:COLORS.green}].map((s,i) => (
          <div key={i} className="card p-4"><p className="stat-label">{s.l}</p><p className="text-xl font-bold mono mt-1" style={{color:s.c}}>{s.v}</p></div>
        ))}
      </div>

      <div className="card p-5">
        <p className="stat-label mb-3">Equity Curve (Live)</p>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={equity}>
              <defs>
                <linearGradient id="liveG" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={COLORS.green} stopOpacity={0.2}/><stop offset="95%" stopColor={COLORS.green} stopOpacity={0}/></linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,43,61,0.4)"/>
              <XAxis dataKey="time" tick={{fontSize:10, fill:'#4a5a70'}} axisLine={false}/>
              <YAxis tick={{fontSize:10, fill:'#4a5a70'}} axisLine={false} domain={['auto','auto']}/>
              <Tooltip contentStyle={{background:'#111820', border:'1px solid #1e2b3d', borderRadius:8, fontSize:11}}/>
              <Area type="monotone" dataKey="value" stroke={COLORS.green} fill="url(#liveG)" strokeWidth={2} name="Equity"/>
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card p-5">
        <p className="stat-label mb-3">Trade PnL Distribution</p>
        <div className="h-[150px]">
          {closedTrades.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={closedTrades.map((t,i) => ({trade: `#${i+1}`, pnl: t.pnl || 0}))}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,43,61,0.4)"/>
              <XAxis dataKey="trade" tick={{fontSize:9, fill:'#4a5a70'}} axisLine={false}/>
              <YAxis tick={{fontSize:10, fill:'#4a5a70'}} axisLine={false}/>
              <Bar dataKey="pnl">{closedTrades.map((t,i) => <Cell key={i} fill={(t.pnl||0) >= 0 ? COLORS.green : COLORS.red} radius={[4,4,0,0]}/>)}</Bar>
              <Tooltip contentStyle={{background:'#111820', border:'1px solid #1e2b3d', borderRadius:8, fontSize:11}}/>
            </BarChart>
          </ResponsiveContainer>
          ) : <p className="text-xs text-center py-12" style={{color:'var(--text-muted)'}}>Trade data will appear as trades close</p>}
        </div>
      </div>
    </div>
  );
}

// ─── PANEL: ALERTS (REAL DATA) ──────────────────────────────
function AlertsPanel({ signals }) {
  const realAlerts = signals.map(sig => ({
    msg: `${sig.direction === 'LONG' ? '🎯' : '🔻'} [${sig.strategy || 'ALGO'}] ${sig.direction} signal on ${sig.symbol}`,
    time: sig.timestamp ? new Date(sig.timestamp).toLocaleTimeString() : 'now'
  }));

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold flex items-center gap-2"><Bell size={18} style={{color:'var(--accent)'}}/> Alerts & Notifications</h2>
        <span className="badge badge-yellow">{realAlerts.length} Total</span>
      </div>

      <div className="card overflow-hidden">
        {realAlerts.length === 0 ? (
          <div className="p-8 text-center" style={{color:'var(--text-muted)'}}><p className="text-xs">No alerts yet — signals will appear as the engine detects them</p></div>
        ) : realAlerts.map((a,i) => (
          <div key={i} className="flex items-center justify-between p-4 border-b transition-colors hover:bg-[rgba(0,212,170,0.03)]" style={{borderColor:'var(--border)'}}>
            <p className="text-sm">{a.msg}</p>
            <span className="text-[10px] whitespace-nowrap ml-4" style={{color:'var(--text-muted)'}}>{a.time}</span>
          </div>
        ))}
      </div>

      <div className="card p-5">
        <p className="stat-label mb-3">Alert Rules</p>
        <div className="space-y-3">
          {['Drawdown > 5%', 'Win rate < 40% (last 20)', 'API disconnected > 30s', 'New signal detected'].map((r,i) => (
            <div key={i} className="flex items-center justify-between">
              <span className="text-sm">{r}</span>
              <div className="toggle-track active"><div className="toggle-thumb" /></div>
            </div>
          ))}
        </div>
      </div>

      <div className="card p-5">
        <p className="stat-label mb-3">Webhook Config</p>
        <div className="space-y-2">
          <div><label className="stat-label">Telegram Bot Token</label><input className="input mt-1" placeholder="bot123456:ABC..." type="password" /></div>
          <div><label className="stat-label">Telegram Chat ID</label><input className="input mt-1" placeholder="-100123456789" /></div>
        </div>
      </div>
    </div>
  );
}

// ─── PANEL: LOGS (REAL DATA) ────────────────────────────────
function LogsPanel({ signals }) {
  const [filter, setFilter] = useState('ALL');
  const lvlColor = { INFO: COLORS.green, WARN: COLORS.yellow, ERROR: COLORS.red, SIGNAL: COLORS.blue };

  // Derive log entries from real signals
  const logs = useMemo(() => {
    const entries = signals.map(sig => ({
      level: 'SIGNAL',
      time: sig.timestamp ? new Date(sig.timestamp).toLocaleTimeString() : '—',
      msg: `[${sig.strategy || 'ALGO'}] ${sig.direction} on ${sig.symbol} | Entry: ${sig.entry || '—'} | Regime: ${sig.regime || '—'}`
    }));
    // Add system entries
    entries.unshift({ level: 'INFO', time: new Date().toLocaleTimeString(), msg: '🤖 Engine v3.0 Active | 20 Algos | 60s cycle' });
    return entries;
  }, [signals]);

  const filtered = filter === 'ALL' ? logs : logs.filter(l => l.level === filter);

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold flex items-center gap-2"><FileText size={18} style={{color:'var(--accent)'}}/> System Logs</h2>
        <div className="flex gap-1">
          {['ALL','INFO','SIGNAL','WARN','ERROR'].map(f => (
            <button key={f} className={`tab ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>{f}</button>
          ))}
        </div>
      </div>

      <div className="card p-4 font-mono text-xs space-y-1 max-h-[500px] overflow-y-auto" style={{background:'var(--bg-primary)'}}>
        {filtered.length === 0 ? (
          <p className="text-center py-8" style={{color:'var(--text-muted)'}}>No log entries matching filter</p>
        ) : filtered.map((l,i) => (
          <div key={i} className="flex gap-2 py-1 px-2 rounded hover:bg-[rgba(30,43,61,0.5)]">
            <span style={{color:'var(--text-muted)'}}>{l.time}</span>
            <span className="font-bold w-16" style={{color: lvlColor[l.level]}}>[{l.level}]</span>
            <span>{l.msg}</span>
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <button className="btn-ghost flex items-center gap-2 text-xs"><Download size={14}/> Export Logs</button>
        <button className="btn-ghost flex items-center gap-2 text-xs"><RefreshCw size={14}/> Refresh</button>
      </div>
    </div>
  );
}

// ─── PANEL: SETTINGS ────────────────────────────────────────
function SettingsPanel({ useTestnet, toggleTradingMode }) {
  return (
    <div className="space-y-4 animate-slide-up">
      <h2 className="text-lg font-bold flex items-center gap-2"><Settings size={18} style={{color:'var(--accent)'}}/> Settings</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-5">
          <p className="stat-label mb-3">🔑 API Configuration</p>
          <div className="space-y-3">
            <div><label className="stat-label">API Key</label><input className="input mt-1" defaultValue="da2f••••••••••••z8k1" type="password" /></div>
            <div><label className="stat-label">API Secret</label><input className="input mt-1" defaultValue="••••••••••••••••" type="password" /></div>
            <div className="flex items-center justify-between pt-2">
              <span className="text-sm">Testnet Mode</span>
              <div className={`toggle-track ${useTestnet ? 'active' : ''}`} onClick={toggleTradingMode}><div className="toggle-thumb"/></div>
            </div>
          </div>
        </div>

        <div className="card p-5">
          <p className="stat-label mb-3">⚙️ Engine Config</p>
          <div className="space-y-3">
            <div className="flex items-center justify-between"><span className="text-sm">Capital (USDT)</span><input className="input w-24 text-center" defaultValue="1000" /></div>
            <div className="flex items-center justify-between"><span className="text-sm">Cycle Interval</span><input className="input w-24 text-center" defaultValue="300s" /></div>
            <div className="flex items-center justify-between"><span className="text-sm">INR Rate</span><input className="input w-24 text-center" defaultValue="84.5" /></div>
            <div className="flex items-center justify-between"><span className="text-sm">Auto-Restart</span><div className="toggle-track active"><div className="toggle-thumb"/></div></div>
          </div>
        </div>
      </div>

      <div className="card p-5">
        <p className="stat-label mb-3">🛡️ Security</p>
        <div className="space-y-2 text-sm" style={{color:'var(--text-secondary)'}}>
          <div className="flex justify-between"><span>Last Login</span><span>Today 02:25 AM</span></div>
          <div className="flex justify-between"><span>IP Whitelist</span><span>Not Configured</span></div>
          <div className="flex justify-between"><span>Session Timeout</span><span>24h</span></div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// ─── MAIN APP ─────────────────────────────────────────────────
// ═══════════════════════════════════════════════════════════════
function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [trades, setTrades] = useState([]);
  const [signals, setSignals] = useState([]);
  const [equity, setEquity] = useState([{ time: 'Start', value: 1000 }]);
  const [balances, setBalances] = useState([]);
  const [useTestnet, setUseTestnet] = useState(true);
  const [showConfirm, setShowConfirm] = useState(false);
  const [botStatus, setBotStatus] = useState('running');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const currentCapital = equity[equity.length - 1]?.value || 1000;

  // ─── FIREBASE LISTENERS ─────────────────────────────────
  useEffect(() => {
    try {
      if (!db) return;
      const qTrades = query(collection(db, 'trades'), orderBy('timestamp', 'desc'), limit(20));
      const unsubTrades = onSnapshot(qTrades, (s) => setTrades(s.docs.map(d => ({ id: d.id, ...d.data() }))));

      const qSignals = query(collection(db, 'signals'), orderBy('timestamp', 'desc'), limit(10));
      const unsubSignals = onSnapshot(qSignals, (s) => setSignals(s.docs.map(d => ({ id: d.id, ...d.data() }))));

      const qEquity = query(collection(db, 'equity'), orderBy('timestamp', 'desc'), limit(50));
      const unsubEquity = onSnapshot(qEquity, (s) => {
        const data = s.docs.map(d => {
          const dd = d.data();
          const t = new Date(dd.timestamp);
          return { time: `${t.getHours()}:${String(t.getMinutes()).padStart(2,'0')}`, value: dd.capital };
        }).reverse();
        if (data.length > 0) setEquity(data);
      });

      const unsubBalances = onSnapshot(doc(db, 'balances', 'current'), (s) => {
        if (s.exists()) setBalances(s.data().assets || []);
      });

      const unsubSettings = onSnapshot(doc(db, 'config', 'bot_settings'), (s) => {
        if (s.exists()) setUseTestnet(s.data().use_testnet ?? true);
      });

      return () => { unsubTrades(); unsubSignals(); unsubEquity(); unsubBalances(); unsubSettings(); };
    } catch (e) { console.warn("Firebase offline", e); }
  }, []);

  const handleModeToggle = () => {
    if (useTestnet) { setShowConfirm(true); }
    else { doToggle(); }
  };

  const doToggle = async () => {
    setShowConfirm(false);
    try {
      const ref = doc(db, 'config', 'bot_settings');
      const snap = await getDoc(ref);
      snap.exists() ? await updateDoc(ref, { use_testnet: !useTestnet }) : await setDoc(ref, { use_testnet: !useTestnet });
    } catch(e) { console.error(e); }
  };

  // ─── RENDER ACTIVE PANEL ────────────────────────────────
  const renderPanel = () => {
    switch(activeTab) {
      case 'dashboard': return <DashboardPanel equity={equity} trades={trades} signals={signals} balances={balances} currentCapital={currentCapital} botStatus={botStatus} useTestnet={useTestnet} />;
      case 'trading': return <TradingPanel />;
      case 'strategies': return <StrategyPanel signals={signals} trades={trades} />;
      case 'portfolio': return <PortfolioPanel trades={trades} balances={balances} />;
      case 'orders': return <OrdersPanel />;
      case 'risk': return <RiskPanel />;
      case 'analytics': return <AnalyticsPanel equity={equity} trades={trades} />;
      case 'alerts': return <AlertsPanel signals={signals} />;
      case 'logs': return <LogsPanel signals={signals} />;
      case 'settings': return <SettingsPanel useTestnet={useTestnet} toggleTradingMode={handleModeToggle} />;
      default: return <DashboardPanel equity={equity} trades={trades} signals={signals} balances={balances} currentCapital={currentCapital} botStatus={botStatus} useTestnet={useTestnet} />;
    }
  };

  let currentSection = '';

  return (
    <div className="flex h-screen overflow-hidden" style={{background:'var(--bg-primary)'}}>
      <ConfirmModal show={showConfirm} title="Switch to LIVE Mode?" message="This will connect to your real exchange account. Real money will be at risk. Are you absolutely sure?" onConfirm={doToggle} onCancel={() => setShowConfirm(false)} />

      {/* ─── SIDEBAR ──────────────────────────────── */}
      <aside className="sidebar hidden lg:flex">
        <div className="p-5 border-b" style={{borderColor:'var(--border)'}}>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center font-black text-sm" style={{background:'var(--accent)', color:'var(--bg-primary)'}}>Q</div>
            <div>
              <p className="text-sm font-bold tracking-tight">QuantBot</p>
              <p className="text-[10px]" style={{color:'var(--text-muted)'}}>v3.0 • 20 Algos</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 py-3 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const showSection = item.section !== currentSection;
            currentSection = item.section;
            return (
              <React.Fragment key={item.id}>
                {showSection && <p className="px-5 pt-4 pb-1.5 text-[10px] font-bold uppercase tracking-widest" style={{color:'var(--text-muted)'}}>{item.section}</p>}
                <div className={`sidebar-link ${activeTab === item.id ? 'active' : ''}`} onClick={() => setActiveTab(item.id)}>
                  <item.icon size={16} />
                  <span>{item.label}</span>
                </div>
              </React.Fragment>
            );
          })}
        </nav>

        {/* Bot Controls */}
        <div className="p-4 border-t space-y-2" style={{borderColor:'var(--border)'}}>
          <div className="flex gap-1.5">
            <button className="btn-ghost flex-1 py-1.5 text-xs flex items-center justify-center gap-1" title="Start"><Play size={12}/></button>
            <button className="btn-ghost flex-1 py-1.5 text-xs flex items-center justify-center gap-1" title="Pause"><Pause size={12}/></button>
            <button className="btn-ghost flex-1 py-1.5 text-xs flex items-center justify-center gap-1 text-red-400" title="Stop"><Square size={12}/></button>
          </div>
        </div>
      </aside>

      {/* ─── MAIN ─────────────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* TOP BAR */}
        <header className="h-14 border-b flex items-center justify-between px-6" style={{background:'var(--bg-secondary)', borderColor:'var(--border)'}}>
          <div className="flex items-center gap-4">
            <h1 className="text-sm font-bold capitalize">{activeTab}</h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <StatusDot status={botStatus} />
              <span className="text-[11px] font-bold capitalize" style={{color:'var(--text-secondary)'}}>{botStatus}</span>
            </div>
            <span className={useTestnet ? 'mode-badge-paper' : 'mode-badge-live'}>{useTestnet ? '📄 PAPER' : '🟢 LIVE'}</span>
            <button className="btn-ghost text-xs py-1.5 px-3" onClick={handleModeToggle}>Switch to {useTestnet ? 'LIVE' : 'PAPER'}</button>
            <button className="kill-switch text-xs py-1.5 px-3" title="Emergency Kill"><Skull size={12}/></button>
          </div>
        </header>

        {/* CONTENT */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-7xl mx-auto">
            {renderPanel()}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
