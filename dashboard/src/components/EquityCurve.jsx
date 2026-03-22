import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { TrendingUp, Percent } from 'lucide-react';

const EquityCurve = ({ history }) => {
  // history is array of { time, equity, drawdown }
  const latestEquity = history.length > 0 ? history[history.length - 1].equity : 0;
  const isUp = history.length > 1 ? latestEquity >= history[0].equity : true;

  return (
    <div className="card p-6 flex flex-col gap-6 h-full">
      <div className="flex justify-between items-start">
        <div className="flex flex-col">
          <h3 className="text-sm font-black uppercase tracking-widest text-[#7a8ba5] mb-1 flex items-center gap-2">
            <TrendingUp size={16} className="text-accent" />
            Equity Curve
          </h3>
          <span className="text-2xl font-black mono text-text-primary">
            ${latestEquity.toLocaleString()}
          </span>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-[10px] text-text-muted font-bold uppercase tracking-widest">Drawdown</span>
          <span className="text-sm font-black text-red mono">
            {history.length > 0 ? history[history.length - 1].drawdown?.toFixed(2) : '0.00'}%
          </span>
        </div>
      </div>

      <div className="w-full h-full min-h-[250px] relative">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={history}>
            <defs>
              <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={isUp ? "#00d4aa" : "#ff4757"} stopOpacity={0.3}/>
                <stop offset="95%" stopColor={isUp ? "#00d4aa" : "#ff4757"} stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2b3d" vertical={false} />
            <XAxis 
              dataKey="time" 
              hide={true}
            />
            <YAxis 
              domain={['auto', 'auto']} 
              hide={true}
            />
            <Tooltip 
              contentStyle={{ background: '#111820', border: '1px solid #1e2b3d', borderRadius: '8px', fontSize: '10px' }}
              labelStyle={{ color: '#4a5a70', fontWeight: 800 }}
              itemStyle={{ color: '#e8edf3', fontWeight: 600 }}
            />
            <Area 
              type="monotone" 
              dataKey="equity" 
              stroke={isUp ? "#00d4aa" : "#ff4757"} 
              fillOpacity={1} 
              fill="url(#colorEquity)" 
              strokeWidth={3}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="pt-4 border-t border-border flex justify-between">
        <div className="flex items-center gap-4">
          <div className="flex flex-col">
            <span className="text-[10px] text-text-muted font-bold uppercase">7D Profit</span>
            <span className="text-xs font-black text-green">+12.4%</span>
          </div>
          <div className="flex flex-col border-l border-border pl-4">
            <span className="text-[10px] text-text-muted font-bold uppercase">Max Drawdown</span>
            <span className="text-xs font-black text-red">8.2%</span>
          </div>
        </div>
        <span className="text-[10px] text-text-muted font-bold underline cursor-pointer">Live Audit Logs</span>
      </div>
    </div>
  );
};

export default EquityCurve;
