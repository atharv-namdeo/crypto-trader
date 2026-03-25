import React from 'react';
import KPICard from '../cards/KPICard';
import CandlestickChart from '../charts/CandlestickChart';
import SignalCard from '../cards/SignalCard';
import StrategyCard from '../cards/StrategyCard';
import RiskCard from '../cards/RiskCard';
import { useSocket } from '../../context/SocketContext';

const Dashboard = () => {
  const { data, connected } = useSocket();

  const portfolio = data?.portfolio || { value: 0, sharpe: 0, drawdown: 0, win_rate: 0, profit_factor: 0 };
  const marketBTC = data?.market?.['BTC/USDT'] || { price: 0, change: 0 };
  const strategies = data?.strategies || {};
  const signals = data?.signals || [];

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* Row 1: KPI Strip */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <KPICard 
          title="Portfolio Value" 
          value={portfolio.value || 0} 
          subValue={`≈ ₹${((portfolio.value || 0) * 84).toLocaleString()}`} 
          trend={(portfolio.value || 0) >= 1000 ? "up" : "down"} 
          trendValue={connected ? "LIVE" : "OFFLINE"}
          prefix="$" 
          color="blue" 
        />
        <KPICard 
          title="24h Change" 
          value={marketBTC.change || 0} 
          suffix="%" 
          color={(marketBTC.change || 0) >= 0 ? "green" : "red"} 
        />
        <KPICard 
          title="Win Rate" 
          value={(portfolio.win_rate || 0) * 100} 
          suffix="%" 
          color="amber" 
        />
        <KPICard 
          title="Active Positions" 
          value={Object.values(strategies).reduce((acc, s) => acc + (s.pos_count || 0), 0)} 
          decimals={0} 
          color="purple" 
        />
        <KPICard 
          title="Sharpe Ratio" 
          value={portfolio.sharpe || 0} 
          subValue="Rolling 24h" 
          color="cyan" 
        />
      </div>

      {/* Row 2: Chart + Signals */}
      <div className="grid grid-cols-1 lg:grid-cols-10 gap-4">
        <div className="lg:col-span-7 card p-4">
           <CandlestickChart data={data?.latest_candles || []} symbol="BTC/USDT" />
        </div>
        
        <div className="lg:col-span-3 card p-4 flex flex-col h-[600px]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-text-primary uppercase flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${connected ? 'bg-accent-primary animate-pulse' : 'bg-accent-danger'}`}></span>
              Live Signals
            </h3>
            <span className="text-[10px] text-text-tertiary uppercase font-bold tracking-widest">Last 50</span>
          </div>
          
          <div className="flex-1 overflow-y-auto pr-2 no-scrollbar">
            {signals.length > 0 ? signals.map((sig, i) => (
              <SignalCard 
                key={i}
                strategy={sig.strategy} 
                symbol={sig.symbol} 
                side={sig.side} 
                score={sig.score || 0} 
                confidence={sig.confidence || 0} 
                time={sig.timestamp ? new Date(sig.timestamp).toLocaleTimeString() : '--'} 
              />
            )) : (
              <div className="text-center text-text-tertiary py-8 italic">Waiting for signals...</div>
            )}
          </div>
        </div>
      </div>

      {/* Row 3: Strategy Performance */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {['scalper', 'swing', 'position'].map(s => {
          const sData = strategies[s] || { trades: 0, wins: 0, pnl: 0, status: 'SCANNING', pos_count: 0 };
          const winRate = sData.trades > 0 ? (sData.wins / sData.trades * 100).toFixed(1) : 0;
          return (
            <StrategyCard 
              key={s}
              name={s.toUpperCase()} 
              status={sData.status} 
              capital={200} 
              trades={sData.trades} 
              winRate={winRate} 
              pnl={(sData.pnl || 0).toFixed(2)} 
              avgHold="--" 
              utilization={sData.pos_count > 0 ? 100 : 0} 
            />
          );
        })}
      </div>

      {/* Row 4: Risk Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pb-8">
        <RiskCard title="Profit Factor" value={(portfolio.profit_factor || 0).toFixed(2)} subValue="Target &gt; 2.0" trend="up" color="green" />
        <RiskCard title="Max Drawdown" value={`${(portfolio.drawdown || 0).toFixed(2)}%`} subValue="Limit 5%" trend="down" color="red" />
        <RiskCard title="Volatility (30d)" value="4.2%" subValue="Historical avg" trend="up" color="amber" />
        <RiskCard title="Liquidity Risk" value="Low" subValue="Slippage < 0.1%" trend="up" color="blue" />
      </div>
    </div>
  );
};

export default Dashboard;
