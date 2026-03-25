import React from 'react';
import { 
  ComposedChart, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  Line, 
  Bar, 
  Cell,
  ReferenceArea
} from 'recharts';

const CandlestickBar = (props) => {
  const { x, y, width, payload } = props;
  const { open, close, high, low } = payload;
  const isGreen = close >= open;
  const color = isGreen ? '#10b981' : '#ef4444';
  
  // Use the Y-axis scale passed through props from Recharts
  const scale = props.yAxis.scale;
  
  const yHigh = scale(high);
  const yLow = scale(low);
  const yOpen = scale(open);
  const yClose = scale(close);
  
  const bodyTop = Math.min(yOpen, yClose);
  const bodyHeight = Math.max(Math.abs(yOpen - yClose), 1);

  return (
    <g>
      {/* Wick (high-low line) */}
      <line 
        x1={x + width / 2} y1={yHigh} 
        x2={x + width / 2} y2={yLow} 
        stroke={color} strokeWidth={1}
      />
      {/* Body */}
      <rect 
        x={x + 1} y={bodyTop} 
        width={width - 2} 
        height={bodyHeight} 
        fill={color} fillOpacity={0.8}
      />
    </g>
  );
};

const CandlestickChart = ({ data, symbol = 'BTC/USDT', timeframe = '1m' }) => {
  if (!data || data.length === 0) return <div className="h-full flex items-center justify-center text-text-tertiary">Loading charts...</div>;

  // Pre-process data to format time if it's a timestamp
  const chartData = data.map(d => ({
    ...d,
    time: typeof d.time === 'number' 
      ? new Date(d.time * 1000).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', hour12: false })
      : d.time
  }));

  return (
    <div className="h-full flex flex-col gap-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <span className="font-bold text-lg text-text-primary px-3 py-1 bg-bg-tertiary rounded border border-border">{symbol}</span>
          <div className="flex bg-bg-secondary rounded border border-border p-0.5">
            {['1m', '5m', '15m', '1h', '4h', '1D'].map((tf) => (
              <button 
                key={tf} 
                className={`px-3 py-1 rounded text-[11px] font-bold uppercase transition-all ${tf === timeframe ? 'bg-accent-primary text-white' : 'text-text-tertiary hover:text-text-secondary'}`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="px-3 py-1 rounded bg-bg-tertiary border border-border text-[11px] font-bold text-text-secondary hover:border-border-bright">Indicators ▼</button>
        </div>
      </div>

      <div className="flex-1 min-h-[400px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <XAxis 
              dataKey="time" 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: '#475569', fontSize: 10 }}
              minTickGap={30}
            />
            <YAxis 
              domain={['auto', 'auto']} 
              orientation="right" 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: '#475569', fontSize: 10, fontFamily: 'JetBrains Mono' }}
            />
            <Tooltip 
              contentStyle={{ background: '#0f0f1a', border: '1px solid #1e1e3a', fontSize: '12px', color: '#f1f5f9' }}
              itemStyle={{ color: '#94a3b8' }}
              cursor={{ stroke: '#1e1e3a', strokeWidth: 1 }}
            />
            
            <Bar dataKey="close" shape={CandlestickBar} />
            
            {/* Indicators */}
            <Line dataKey="ema9" dot={false} stroke="#06b6d4" strokeWidth={1} />
            <Line dataKey="ema21" dot={false} stroke="#f97316" strokeWidth={1} />
            <Line dataKey="vwap" dot={false} stroke="#8b5cf6" strokeWidth={1} strokeDasharray="3 3" />
            
            {/* Volume at bottom */}
            <Bar dataKey="volume" yAxisId="volume" fill="#3b82f6" fillOpacity={0.1} />
            <YAxis yAxisId="volume" hide domain={[0, dataMax => dataMax * 5]} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 gap-4 h-[100px]">
        <div className="card bg-bg-secondary p-2 flex flex-col">
          <span className="text-[10px] font-bold text-text-tertiary uppercase mb-1">RSI (14)</span>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData}>
              <XAxis dataKey="time" hide />
              <YAxis domain={[0, 100]} hide />
              <Line dataKey="rsi" dot={false} stroke="#8b5cf6" strokeWidth={1.5} />
              <ReferenceArea y1={30} y2={70} fill="#1e1e3a" fillOpacity={0.2} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <div className="card bg-bg-secondary p-2 flex flex-col">
          <span className="text-[10px] font-bold text-text-tertiary uppercase mb-1">MACD</span>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData}>
              <XAxis dataKey="time" hide />
              <YAxis hide />
              <Bar dataKey="macd_hist" fill="#3b82f6" fillOpacity={0.5}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.macd_hist > 0 ? '#10b981' : '#ef4444'} />
                ))}
              </Bar>
              <Line dataKey="macd_signal" dot={false} stroke="#f97316" strokeWidth={1} />
              <Line dataKey="macd_line" dot={false} stroke="#3b82f6" strokeWidth={1} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default CandlestickChart;
