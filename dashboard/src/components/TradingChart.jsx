import React, { useState, useEffect, useRef } from 'react';
import { 
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, ReferenceDot, Scatter, ScatterChart 
} from 'recharts';
import { Maximize2, ZoomIn, ZoomOut, Move } from 'lucide-react';

const COLORS = {
  SCALPER: '#00ffff',
  SWING: '#8b5cf6',
  POSITION: '#f97316',
  BUY: '#10b981',
  SELL: '#ef4444',
  CLOSE: '#ffffff',
  TP: '#facc15',
  SL: '#ef4444'
};

const STRATEGY_COLORS = {
  SCALPER: 'text-cyan-400',
  SWING: 'text-purple-400',
  POSITION: 'text-orange-400'
};

const TradingChart = ({ symbol, timeframe, initialCandles, signals }) => {
  const [chartData, setChartData] = useState([]);
  const [visibleCount, setVisibleCount] = useState(100);
  const [panOffset, setPanOffset] = useState(0);
  const chartRef = useRef(null);

  // Append new candles, keep last 200
  useEffect(() => {
    if (!initialCandles || initialCandles.length === 0) return;
    
    setChartData(prev => {
      const combined = [...prev, ...initialCandles.filter(
        c => !prev.find(p => p.time === c.time)
      )];
      // Sort by time
      combined.sort((a, b) => a.time - b.time);
      return combined.slice(-200);
    });
  }, [initialCandles]);

  // Handle Zoom (Mouse Wheel)
  const handleWheel = (e) => {
    if (e.deltaY < 0) {
      setVisibleCount(prev => Math.max(10, prev - 5));
    } else {
      setVisibleCount(prev => Math.min(200, prev + 5));
    }
  };

  // Prepare visible data
  const dataSlice = chartData.slice(-(visibleCount + panOffset), panOffset === 0 ? undefined : -panOffset);
  const xMin = dataSlice[0]?.time;
  const xMax = dataSlice[dataSlice.length - 1]?.time;

  return (
    <div className="card p-4 h-full flex flex-col gap-4 relative" onWheel={handleWheel}>
      <div className="flex justify-between items-center px-2">
        <div className="flex items-center gap-4">
          <h3 className="text-sm font-black text-text-primary uppercase tracking-tighter">
            {symbol} / <span className="text-accent">{timeframe}</span>
          </h3>
          <div className="flex gap-2 items-center text-[10px] font-bold text-text-muted">
             <div className="flex items-center gap-1"><ZoomIn size={12}/> Scroll to Zoom</div>
             <div className="flex items-center gap-1 ml-2"><Move size={12}/> Drag to Pan</div>
          </div>
        </div>
        <div className="flex gap-2">
           <button className="p-1 hover:text-accent"><Maximize2 size={16}/></button>
        </div>
      </div>

      <div className="flex-1 w-full min-h-[350px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={dataSlice}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2b3d" vertical={false} opacity={0.5} />
            <XAxis 
              dataKey="time" 
              domain={[xMin, xMax]}
              type="number"
              scale="time"
              tickFormatter={(t) => new Date(t * 1000).toLocaleTimeString('en-IN', {
                timeZone: 'Asia/Kolkata',
                hour: '2-digit',
                minute: '2-digit'
              })}
              tick={{ fill: '#4a5a70', fontSize: 10, fontWeight: 800 }}
              axisLine={false}
              minTickGap={30}
            />
            <YAxis 
              domain={['auto', 'auto']} 
              tick={{ fill: '#4a5a70', fontSize: 10, fontWeight: 800 }}
              orientation="right"
              axisLine={false}
              tickFormatter={(v) => v.toLocaleString()}
            />
            <Tooltip 
              contentStyle={{ background: '#111820', border: '1px solid #1e2b3d', borderRadius: '8px', fontSize: '11px' }}
              labelStyle={{ color: '#4a5a70', fontWeight: 800 }}
              itemStyle={{ color: '#e8edf3', fontWeight: 600 }}
              labelFormatter={(t) => new Date(t * 1000).toLocaleString()}
            />
            
            <Bar dataKey="volume" fill="rgba(0, 212, 170, 0.1)" yAxisId="0" />
            <Line 
              type="monotone" 
              dataKey="close" 
              stroke="#00d4aa" 
              strokeWidth={2} 
              dot={false} 
              activeDot={{ r: 4, stroke: '#fff', strokeWidth: 2 }}
            />

            {/* Signal Markers */}
            {signals.map((sig, i) => {
              // Only render if in visible range
              if (sig.time < xMin || sig.time > xMax) return null;
              
              const isBuy = sig.action === 'OPEN' && sig.type === 'LONG';
              const isShort = sig.action === 'OPEN' && sig.type === 'SHORT';
              const isClose = sig.action === 'CLOSE';
              
              const color = COLORS[sig.strategy] || '#fff';
              const icon = isBuy ? '▲' : isShort ? '▼' : '●';
              const yPos = isBuy ? sig.price * 0.999 : isShort ? sig.price * 1.001 : sig.price;

              return (
                <ReferenceDot
                  key={i}
                  x={sig.time}
                  y={sig.price}
                  r={isClose ? 4 : 6}
                  fill={isClose ? '#fff' : (isBuy ? COLORS.BUY : COLORS.SELL)}
                  stroke={color}
                  strokeWidth={2}
                  label={{
                    value: icon,
                    position: isBuy ? 'bottom' : 'top',
                    fill: isBuy ? COLORS.BUY : (isShort ? COLORS.SELL : '#fff'),
                    fontSize: 14,
                    fontWeight: 900
                  }}
                />
              );
            })}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="flex flex-wrap items-center gap-6 px-4 py-2 bg-bg-secondary/50 rounded-xl border border-border/40">
        <div className="flex items-center gap-4 border-r border-border pr-6">
           <LegendItem icon="▲" label="Long Entry" color={COLORS.BUY} />
           <LegendItem icon="▼" label="Short Entry" color={COLORS.SELL} />
           <LegendItem icon="●" label="Close" color="#fff" />
        </div>
        <div className="flex items-center gap-4">
           <LegendItem icon="■" label="Scalper" color={COLORS.SCALPER} />
           <LegendItem icon="■" label="Swing" color={COLORS.SWING} />
           <LegendItem icon="■" label="Position" color={COLORS.POSITION} />
        </div>
      </div>
    </div>
  );
};

const LegendItem = ({ icon, label, color }) => (
  <div className="flex items-center gap-1.5">
    <span style={{ color }}>{icon}</span>
    <span className="text-[10px] font-black uppercase text-text-muted">{label}</span>
  </div>
);

export default TradingChart;
