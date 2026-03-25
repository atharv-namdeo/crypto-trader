import React from 'react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';

const EquityCurve = ({ data }) => {
  // If data exists, it's a list of {time, value, strategy}
  // We need to map 'value' to 'total' for the chart
  const processedData = data && data.length > 0 
    ? [...data].reverse().map(d => ({ ...d, total: d.value }))
    : Array.from({ length: 30 }).map((_, i) => ({
        time: `Day ${i + 1}`,
        total: 1000 + i * 50 + (Math.random() - 0.5) * 200,
      }));

  return (
    <div className="h-[400px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={processedData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.1}/>
              <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e1e3a" vertical={false} />
          <XAxis 
            dataKey="time" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#475569', fontSize: 10 }}
          />
          <YAxis 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#475569', fontSize: 10, fontFamily: 'JetBrains Mono' }}
            domain={['auto', 'auto']}
            orientation="right"
          />
          <Tooltip 
            contentStyle={{ background: '#0f0f1a', border: '1px solid #1e1e3a', borderRadius: '6px' }}
            itemStyle={{ fontSize: '12px' }}
            formatter={(value) => [`$${value.toLocaleString()}`, 'Equity']}
          />
          
          <Area 
            type="monotone" 
            dataKey="total" 
            stroke="#10b981" 
            fillOpacity={1} 
            fill="url(#colorTotal)" 
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default EquityCurve;
