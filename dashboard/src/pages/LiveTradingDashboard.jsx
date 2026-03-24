import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import { AlertCircle, TrendingUp, TrendingDown, Activity, ShieldCheck, Gauge } from 'lucide-react';

const LiveTradingDashboard = ({ ws }) => {
  const [metrics, setMetrics] = useState({
    account_value: 0,
    daily_pnl: 0,
    win_rate: 0,
    drawdown: 0,
    phase: 'SCANNING',
    models_accuracy: {},
  });

  const [equityHistory, setEquityHistory] = useState([]);
  const [tradeHistory, setTradeHistory] = useState([]);
  const [rollout, setRollout] = useState({ phase: 'N/A', elapsed_days: 0 });

  useEffect(() => {
    if (!ws) return;

    const handleUpdate = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === 'METRICS_UPDATE') {
          setMetrics(prev => ({ ...prev, ...msg.data }));
        }

        if (msg.type === 'engine_update' && msg.data.equity_history) {
           const history = msg.data.equity_history.map(e => ({
             time: new Date(e.timestamp).toLocaleTimeString(),
             value: e.equity || e.value
           })).reverse();
           setEquityHistory(history);
        }

        if (msg.type === 'ROLLOUT_UPDATE') {
          setRollout({ phase: msg.phase, elapsed_days: msg.elapsed_days });
        }

        if (msg.type === 'TRADE_EXECUTED') {
          setTradeHistory(prev => [
            { ...msg.data, time: new Date(msg.timestamp).toLocaleTimeString() },
            ...prev
          ].slice(-10));
        }
      } catch (e) {
        // console.error('Dashboard update error:', e);
      }
    };

    ws.addEventListener('message', handleUpdate);
    return () => ws.removeEventListener('message', handleUpdate);
  }, [ws]);

  const COLORS = ['#06b6d4', '#8b5cf6', '#f97316', '#ec4899'];

  return (
    <div className="p-6 space-y-6 bg-bg-primary min-h-screen text-text-primary">
      {/* Header Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-bg-secondary p-4 rounded-xl border border-border/50 shadow-xl">
          <p className="text-text-muted text-xs font-bold uppercase tracking-wider mb-1">Account Value</p>
          <p className="text-2xl font-black text-accent">${metrics.account_value.toLocaleString()}</p>
        </div>
        <div className="bg-bg-secondary p-4 rounded-xl border border-border/50 shadow-xl">
          <p className="text-text-muted text-xs font-bold uppercase tracking-wider mb-1">Daily P/L</p>
          <p className={`text-2xl font-black ${metrics.daily_pnl >= 0 ? 'text-green' : 'text-red'}`}>
            {metrics.daily_pnl >= 0 ? '+' : ''}${metrics.daily_pnl.toFixed(2)}
          </p>
        </div>
        <div className="bg-bg-secondary p-4 rounded-xl border border-border/50 shadow-xl">
          <p className="text-text-muted text-xs font-bold uppercase tracking-wider mb-1">Win Rate</p>
          <p className="text-2xl font-black text-purple-400">{(metrics.win_rate * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-bg-secondary p-4 rounded-xl border border-border/50 shadow-xl">
          <p className="text-text-muted text-xs font-bold uppercase tracking-wider mb-1">Max Drawdown</p>
          <p className={`text-2xl font-black ${metrics.drawdown < 10 ? 'text-green' : 'text-orange-400'}`}>
            {metrics.drawdown.toFixed(1)}%
          </p>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Rollout & Equity */}
        <div className="lg:col-span-2 space-y-6">
          {/* Rollout Status */}
          <div className="bg-bg-secondary p-6 rounded-2xl border border-border/50 shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <ShieldCheck size={80} />
            </div>
            <h3 className="text-lg font-black uppercase tracking-tighter mb-4 flex items-center gap-2">
              <Activity className="text-accent" /> Graduated Rollout Status
            </h3>
            <div className="flex flex-wrap items-end gap-6">
              <div>
                <p className="text-text-muted text-[10px] font-black uppercase">Current Phase</p>
                <p className="text-3xl font-black text-accent">{rollout.phase}</p>
              </div>
              <div className="flex-1">
                <div className="flex justify-between text-[10px] font-black uppercase mb-1">
                  <span>Progress</span>
                  <span>{rollout.elapsed_days} Days / Phase</span>
                </div>
                <div className="w-full bg-bg-tertiary h-2 rounded-full overflow-hidden">
                  <div 
                    className="bg-accent h-full transition-all duration-1000" 
                    style={{ width: `${Math.min(100, (rollout.elapsed_days / 7) * 100)}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>

          {/* Equity Chart */}
          <div className="bg-bg-secondary p-6 rounded-2xl border border-border/50 shadow-2xl h-[400px]">
            <h3 className="text-lg font-black uppercase tracking-tighter mb-6">Performance Trajectory</h3>
            <ResponsiveContainer width="100%" height="90%">
              <AreaChart data={equityHistory}>
                <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00f3ff" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#00f3ff" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                <XAxis dataKey="time" stroke="#444" fontSize={10} fontStyle="bold" />
                <YAxis stroke="#444" fontSize={10} fontStyle="bold" domain={['auto', 'auto']} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0a0a0a', border: '1px solid #222', borderRadius: '8px' }}
                  itemStyle={{ color: '#00f3ff', fontWeight: 'bold' }}
                />
                <Area type="monotone" dataKey="value" stroke="#00f3ff" strokeWidth={3} fillOpacity={1} fill="url(#colorValue)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right Column: Distribution & Recent Trades */}
        <div className="space-y-6">
          <div className="bg-bg-secondary p-6 rounded-2xl border border-border/50 shadow-2xl">
            <h3 className="text-lg font-black uppercase tracking-tighter mb-4">Strategy Volume</h3>
            <div className="h-[250px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Scalper', value: 35 },
                      { name: 'Swing', value: 25 },
                      { name: 'Position', value: 20 },
                      { name: 'ML Ensemble', value: 20 },
                    ]}
                    cx="50%" cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {COLORS.map((color, idx) => <Cell key={idx} fill={color} />)}
                  </Pie>
                  <Tooltip />
                  <Legend verticalAlign="bottom" height={36}/>
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-bg-secondary p-4 rounded-2xl border border-border/50 shadow-2xl max-h-[460px] overflow-hidden flex flex-col">
             <h3 className="text-lg font-black uppercase tracking-tighter mb-4">Live Execution</h3>
             <div className="space-y-3 overflow-y-auto pr-2">
                {tradeHistory.map((trade, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-bg-tertiary/50 rounded-xl border border-border/20">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${trade.side === 'BUY' ? 'bg-green/10 text-green' : 'bg-red/10 text-red'}`}>
                        {trade.side === 'BUY' ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                      </div>
                      <div>
                        <p className="text-xs font-black leading-none">{trade.symbol}</p>
                        <p className="text-[10px] text-text-muted font-bold">{trade.strategy}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`text-xs font-black leading-none ${trade.pnl >= 0 ? 'text-green' : 'text-red'}`}>
                        {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                      </p>
                      <p className="text-[10px] text-text-muted font-bold">{trade.time}</p>
                    </div>
                  </div>
                ))}
                {tradeHistory.length === 0 && <p className="text-center py-10 text-text-muted text-xs font-bold uppercase tracking-widest">Waiting for trades...</p>}
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LiveTradingDashboard;
