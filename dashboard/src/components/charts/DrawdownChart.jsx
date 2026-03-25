import React from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';

const DrawdownChart = ({ data }) => {
  const defaultData = Array.from({ length: 30 }).map((_, i) => ({
    time: `Mar ${i + 1}`,
    drawdown: -Math.random() * 2.5
  }));

  return (
    <div className="h-[150px] w-full mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data || defaultData} margin={{ top: 0, right: 30, left: 0, bottom: 0 }}>
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
            tick={{ fill: '#ef4444', fontSize: 10, fontFamily: 'JetBrains Mono' }}
            domain={['-auto', 0]}
          />
          <Tooltip 
            contentStyle={{ background: '#0f0f1a', border: '1px solid #1e1e3a', borderRadius: '6px' }}
            itemStyle={{ fontSize: '12px', color: '#ef4444' }}
            formatter={(value) => [`${value.toFixed(2)}%`, 'Drawdown']}
          />
          <Bar 
            dataKey="drawdown" 
            fill="#ef4444" 
            fillOpacity={0.4} 
            radius={[0, 0, 4, 4]} 
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default DrawdownChart;
