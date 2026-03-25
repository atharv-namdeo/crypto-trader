import React from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ReferenceLine } from 'recharts';

const SignalHeatmap = ({ data = [] }) => {
  // Mocking 24h data if empty
  const chartData = data.length > 0 ? data : Array.from({ length: 24 }, (_, i) => ({
    hour: `${i}h`,
    score: (Math.random() - 0.5) * 200,
    volume: Math.random() * 100
  }));

  return (
    <div className="card p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-sm font-bold text-text-primary uppercase tracking-tight">Signal Distribution (24h)</h3>
        <div className="flex gap-4">
          <span className="text-[10px] text-accent-success font-bold uppercase tracking-widest">Bullish</span>
          <span className="text-[10px] text-accent-danger font-bold uppercase tracking-widest">Bearish</span>
        </div>
      </div>

      <div className="flex-1 min-h-[250px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <XAxis 
              dataKey="hour" 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: '#475569', fontSize: 10, fontWeight: 600 }} 
            />
            <YAxis hide domain={[-100, 100]} />
            <Tooltip 
              cursor={{ fill: '#1a1a35', opacity: 0.4 }}
              contentStyle={{ background: '#0f0f1a', border: '1px solid #1e1e3a', borderRadius: '4px', fontSize: '11px' }}
            />
            <ReferenceLine y={0} stroke="#1e1e3a" />
            <Bar dataKey="score" radius={[2, 2, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.score >= 0 ? '#10b981' : '#ef4444'} 
                  fillOpacity={Math.abs(entry.score) / 100 + 0.2} 
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 flex items-center justify-between text-[10px] text-text-tertiary font-bold uppercase tracking-widest border-t border-border pt-4">
        <span>-24h</span>
        <span>Current Intensity</span>
        <span>Now</span>
      </div>
    </div>
  );
};

export default SignalHeatmap;
