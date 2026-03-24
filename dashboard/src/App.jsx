import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import MobileNav from './components/MobileNav';
import MarketTicker from './components/MarketTicker';
import StrategyCards from './components/StrategyCards';
import FuzzyRadar from './components/FuzzyRadar';
import OpenPositions from './components/OpenPositions';
import EquityCurve from './components/EquityCurve';
import RiskMetrics from './components/RiskMetrics';
import LiveLogs from './components/LiveLogs';
import SettingsPanel from './components/SettingsPanel';
import TradeHistory from './components/TradeHistory';
import SignalHeatmap from './components/SignalHeatmap';
import TradingChart from './components/TradingChart';
import MLSignalPanel from './components/MLSignalPanel';
import MultiAssetMonitor from './components/MultiAssetMonitor';
import LiveTradingDashboard from './pages/LiveTradingDashboard';

const API_BASE = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`;
// Fallback logic: if VITE_WS_URL is missing, derive it from API_BASE
const WS_BASE = import.meta.env.VITE_WS_URL || 
  (API_BASE.startsWith('https') 
    ? API_BASE.replace('https', 'wss').replace(/\/$/, '') + '/ws'
    : API_BASE.replace('http', 'ws').replace(/\/$/, '') + '/ws');

console.log('API_BASE:', API_BASE);
console.log('WS_BASE:', WS_BASE);

const App = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [timeframe, setTimeframe] = useState('1h');
  const [chartCandles, setChartCandles] = useState([]);
  const [wsStatus, setWsStatus] = useState('OFFLINE');
  const [errorCount, setErrorCount] = useState(0);
  const [ws, setWs] = useState(null);
  const [data, setData] = useState({
    market: {},
    strategies: {},
    portfolio: { sharpe: 0, profit_factor: 0, win_rate: 0, max_drawdown: 0 },
    equity_history: [],
    logs: [],
    positions: [],
    signals: [],
    settings: {
      scalper_enabled: 'true', scalper_threshold: 0.45,
      swing_enabled: 'true', swing_threshold: 0.55,
      position_enabled: 'true', position_threshold: 0.65
    }
  });

  const fetchCandles = async (tf) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    try {
      const res = await fetch(`${API_BASE}/candles?symbol=BTC/USDT&interval=${tf}&limit=200`, {
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      const candles = await res.json();
      setChartCandles(candles);
    } catch (e) {
      if (e.name === 'AbortError') console.warn('Fetch candles timed out');
      else console.error('Fetch candles error:', e);
    }
  };

  useEffect(() => {
    fetchCandles(timeframe);
  }, [timeframe]);

  useEffect(() => {
    let socket;
    let reconnectTimer;

    const connect = () => {
      socket = new WebSocket(WS_BASE);
      setWs(socket);
      
      socket.onopen = () => {
        console.log('✅ WebSocket Connected');
        setWsStatus('CONNECTED');
        setErrorCount(0);
      };

      socket.onerror = (e) => {
        console.error('❌ WebSocket Error:', e);
        setWsStatus('ERROR');
        setErrorCount(prev => prev + 1);
      };

      socket.onclose = () => {
        console.warn('⚠️ WebSocket Closed. Reconnecting in 3s...');
        setWsStatus('OFFLINE');
        reconnectTimer = setTimeout(connect, 3000);
      };
      
      socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'info') {
            console.info('📬 Backend Info:', msg.data);
            if (msg.data.includes('Redis')) setWsStatus('WAITING_REDIS');
          } else if (msg.type === 'engine_update') {
            setWsStatus('LIVE');
            setData(prev => {
              const newData = { ...prev, ...msg.data };
              if (msg.data.portfolio && typeof msg.data.portfolio === 'object') {
                 newData.portfolio = { ...prev.portfolio, ...msg.data.portfolio };
              }
              return newData;
            });

            if (msg.data.latest_candles && msg.data.latest_candles[timeframe]) {
              const newCandle = msg.data.latest_candles[timeframe][0];
              if (newCandle) {
                setChartCandles([newCandle]);
              }
            }
          }
        } catch (je) {
          console.error('Unsafe JSON parsing detected from WebSocket:', je);
        }
      };
    };

    connect();
    return () => {
      if (socket) socket.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, [timeframe]);

  const handleAction = async (type, payload) => {
    console.log('Action:', type, payload);
    const res = await fetch(`${API_BASE}/api/v1/order`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: type, ...payload })
    });
    return res.json();
  };

  const updateSettings = async (key, value) => {
    await fetch(`${API_BASE}/api/v1/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [key]: value })
    });
  };

  return (
    <div className="flex h-screen bg-bg-primary text-text-primary overflow-hidden">
      <Sidebar activeTab={activeTab} setTab={setActiveTab} botStatus="ONLINE" />
      
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto pb-24 md:pb-0">
        <MarketTicker marketData={data.market} metrics={data.portfolio} />
        
        <div className="p-4 space-y-6">
          {activeTab === 'dashboard' && (
            <>
              <MultiAssetMonitor marketData={data.market} signals={data.signals} />
              
              <div className="flex justify-between items-center mb-4 mt-6">
                <StrategyCards stats={data.strategies} />
                <div className="flex gap-2 bg-bg-secondary p-1 rounded-lg border border-border/50">
                  {['1m', '5m', '15m', '1h', '4h', '1d'].map(tf => (
                    <button
                      key={tf}
                      onClick={() => setTimeframe(tf)}
                      className={`px-3 py-1 rounded-md text-[10px] font-black uppercase transition-all ${
                        timeframe === tf ? 'bg-accent text-bg-primary shadow-lg shadow-accent/20' : 'hover:bg-bg-tertiary text-text-muted'
                      }`}
                    >
                      {tf}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                  wsStatus === 'LIVE' ? 'bg-green/10 text-green border-green/20' :
                  wsStatus === 'CONNECTED' ? 'bg-blue/10 text-blue border-blue/20' :
                  wsStatus === 'WAITING_REDIS' ? 'bg-yellow/10 text-yellow border-yellow/20' :
                  'bg-red/10 text-red border-red/20'
                }`}>
                  {wsStatus} {errorCount > 0 && `(${errorCount})`}
                </div>
                <span className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest font-black text-text-muted">
                  <span className="w-1.5 h-1.5 bg-accent rounded-full animate-ping"></span>
                  Live WebSocket Engine V6.5
                </span>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-6">
                  <div className="h-[450px]">
                    <TradingChart 
                      symbol="BTC/USDT" 
                      timeframe={timeframe} 
                      initialCandles={chartCandles} 
                      signals={data.signals} 
                    />
                  </div>
                  <OpenPositions positions={data.positions} onAction={handleAction} />
                </div>
                <div className="space-y-6">
                  <MLSignalPanel ws={ws} />
                  <FuzzyRadar fuzzyScores={data.market['BTC/USDT']?.fuzzy || data.market['BTC/USDT'] || {}} />
                  <EquityCurve history={data.equity_history} />
                  <SignalHeatmap data={[]} />
                </div>
              </div>
            </>
          )}

          {activeTab === 'live' && <LiveTradingDashboard ws={ws} />}

          {activeTab === 'trading' && (
            <div className="space-y-6">
               <div className="h-[600px]">
                  <TradingChart 
                    symbol="BTC/USDT" 
                    timeframe={timeframe} 
                    initialCandles={chartCandles} 
                    signals={data.signals} 
                  />
               </div>
               <OpenPositions positions={data.positions} onAction={handleAction} />
            </div>
          )}
          {activeTab === 'signals' && <SignalHeatmap data={[]} />}
          {activeTab === 'portfolio' && (
            <div className="space-y-6">
              <RiskMetrics metrics={data.portfolio} />
              <EquityCurve history={data.equity_history} />
            </div>
          )}
          {activeTab === 'settings' && <SettingsPanel settings={data.settings} onUpdate={updateSettings} />}
          
          <LiveLogs logs={data.logs} />
          <TradeHistory trades={[]} />
        </div>
      </main>

      <MobileNav activeTab={activeTab} setTab={setActiveTab} />
    </div>
  );
};

export default App;
