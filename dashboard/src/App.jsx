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

const App = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [timeframe, setTimeframe] = useState('1h');
  const [chartCandles, setChartCandles] = useState([]);
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
    try {
      const res = await fetch(`http://${window.location.hostname}:8000/candles?symbol=BTC/USDT&interval=${tf}&limit=200`);
      const candles = await res.json();
      setChartCandles(candles);
    } catch (e) {
      console.error('Fetch candles error:', e);
    }
  };

  useEffect(() => {
    fetchCandles(timeframe);
  }, [timeframe]);

  useEffect(() => {
    const ws = new WebSocket(`ws://${window.location.hostname}:8000/ws`);
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'engine_update') {
        setData(prev => ({ ...prev, ...msg.data }));
        
        // Update chart with latest candle if it matches timeframe
        if (msg.data.latest_candles && msg.data.latest_candles[timeframe]) {
          const newCandle = msg.data.latest_candles[timeframe][0];
          if (newCandle) {
            setChartCandles([newCandle]); // TradingChart handles the append logic via useEffect
          }
        }
      }
    };
    return () => ws.close();
  }, []);

  const handleAction = async (type, payload) => {
    console.log('Action:', type, payload);
    const res = await fetch(`http://${window.location.hostname}:8000/api/v1/order`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: type, ...payload })
    });
    return res.json();
  };

  const updateSettings = async (key, value) => {
    await fetch(`http://${window.location.hostname}:8000/api/v1/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ [key]: value })
    });
  };

  return (
    <div className="flex h-screen bg-bg-primary text-text-primary overflow-hidden">
      <Sidebar activeTab={activeTab} setTab={setActiveTab} botStatus="ONLINE" />
      
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto pb-20 md:pb-0">
        <MarketTicker marketData={data.market} metrics={data.portfolio} />
        
        <div className="p-4 space-y-6">
          {activeTab === 'dashboard' && (
            <>
              <div className="flex justify-between items-center mb-4">
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
                  <FuzzyRadar fuzzyScores={data.market['BTC/USDT']?.fuzzy || data.market['BTC/USDT'] || {}} />
                  <EquityCurve history={data.equity_history} />
                  <SignalHeatmap data={[]} />
                </div>
              </div>
            </>
          )}

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
