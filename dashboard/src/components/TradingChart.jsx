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
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState(0);

  // Append new candles, keep last 500 for better panning history
  useEffect(() => {
    if (!initialCandles || initialCandles.length === 0) return;
    
    setChartData(prev => {
      const combined = [...prev, ...initialCandles.filter(
        c => !prev.find(p => p.time === c.time)
      )];
      combined.sort((a, b) => a.time - b.time);
      return combined.slice(-500);
    });
  }, [initialCandles]);

  // Handle Zoom (Mouse Wheel)
  const handleWheel = (e) => {
    if (e.deltaY < 0) {
      setVisibleCount(prev => Math.max(20, prev - 10));
    } else {
      setVisibleCount(prev => Math.min(500, prev + 10));
    }
  };

  // Panning logic
  const handleMouseDown = (e) => {
    setIsDragging(true);
    setDragStart(e.clientX);
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    const delta = e.clientX - dragStart;
    if (Math.abs(delta) > 5) {
      const shift = Math.round(delta / 5);
      setPanOffset(prev => {
        const newVal = prev + shift; // Reverse logic: drag right -> more history -> higher panOffset? 
        // Wait: slice(-start, -end). Pan right (delta > 0) -> see OLDER data -> Increase panOffset.
        // Pan left (delta < 0) -> see NEWER data -> Decrease panOffset.
        const maxOffset = Math.max(0, chartData.length - visibleCount);
        return Math.max(0, Math.min(maxOffset, newVal));
      });
      setDragStart(e.clientX);
    }
  };

  const handleMouseUp = () => setIsDragging(false);

  // Prepare visible data
  const dataSlice = chartData.slice(
    Math.max(0, chartData.length - visibleCount - panOffset),
    panOffset === 0 ? undefined : Math.max(1, chartData.length - panOffset)
  );

  const xMin = dataSlice[0]?.time;
  const xMax = dataSlice[dataSlice.length - 1]?.time;

  return (
    <div 
      className={`card p-4 h-full flex flex-col gap-4 relative select-none ${isDragging ? 'cursor-grabbing' : 'cursor-default'}`}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
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
            <div className="text-[10px] font-bold text-accent bg-accent/10 px-2 py-0.5 rounded border border-accent/20">
              {dataSlice.length} CANDLES
            </div>
           <button className="p-1 hover:text-accent"><Maximize2 size={16}/></button>
        </div>
      </div>

      <div className="flex-1 w-full min-h-[350px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={dataSlice}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2b3d" vertical={false} opacity={0.5} />
            <XAxis 
              dataKey="time" 
              domain={['dataMin', 'dataMax']}
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
              allowDataOverflow={true}
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
              isAnimationActive={false}
              activeDot={{ r: 4, stroke: '#fff', strokeWidth: 2 }}
            />

            {/* Render Signals using ReferenceDots for precise placement */}
            {signals.map((sig, i) => {
              if (sig.time < xMin || sig.time > xMax) return null;
              
              const isBuy = (sig.action === 'OPEN' && sig.type === 'LONG') || (sig.action === 'CLOSE' && sig.type === 'SHORT');
              const isSell = (sig.action === 'OPEN' && sig.type === 'SHORT') || (sig.action === 'CLOSE' && sig.type === 'LONG');
              const isClose = sig.action === 'CLOSE';
              
              const color = COLORS[sig.strategy] || '#fff';
              const icon = isBuy ? '▲' : isSell ? '▼' : '●';

              return (
                <ReferenceDot
                  key={`signal-${sig.time}-${i}`}
                  x={sig.time}
                  y={sig.price}
                  r={isClose ? 4 : 6}
                  fill={isClose ? '#fff' : (isBuy ? COLORS.BUY : COLORS.SELL)}
                  stroke={color}
                  strokeWidth={2}
                  isAnimationActive={false}
                  label={{
                    value: icon,
                    position: isBuy ? 'bottom' : 'top',
                    fill: isBuy ? COLORS.BUY : (isSell ? COLORS.SELL : '#fff'),
                    fontSize: 16,
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
           <LegendItem icon="▲" label="Buy/Long" color={COLORS.BUY} />
           <LegendItem icon="▼" label="Sell/Short" color={COLORS.SELL} />
           <LegendItem icon="●" label="Close" color="#fff" />
        </div>
        <div className="flex items-center gap-4 text-[10px] font-bold text-text-muted">
           Strategies: 
           <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full" style={{background: COLORS.SCALPER}}/> Scalper</div>
           <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full" style={{background: COLORS.SWING}}/> Swing</div>
           <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full" style={{background: COLORS.POSITION}}/> Position</div>
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
