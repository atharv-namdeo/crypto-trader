import React from 'react';
import { LayoutGrid, Info } from 'lucide-react';

const SignalHeatmap = ({ data }) => {
  // data is array of 24 numbers [-1 to 1]
  // Mocking 24 hours if data is empty
  const heatmapData = data.length === 24 ? data : Array.from({ length: 24 }, (_, i) => Math.sin(i * 0.5) * 0.8);

  return (
    <div className="card p-6 flex flex-col gap-6">
      <div className="flex justify-between items-center">
        <h3 className="text-sm font-black uppercase tracking-widest text-[#7a8ba5] flex items-center gap-2">
          <LayoutGrid size={16} className="text-accent" />
          24H Signal Intensity
        </h3>
        <Info size={14} className="text-text-muted cursor-help" />
      </div>

      <div className="grid grid-cols-6 md:grid-cols-12 gap-2">
        {heatmapData.map((val, idx) => (
          <div 
            key={idx} 
            className={`aspect-square rounded-md border border-border/50 flex items-center justify-center transition-all duration-300 hover:scale-110 hover:shadow-lg cursor-default relative group`}
            style={{ 
              background: getHeatmapColor(val),
              borderColor: val === 0 ? 'var(--border)' : 'transparent'
            }}
          >
             <span className="text-[8px] font-black text-white opacity-0 group-hover:opacity-100 transition-opacity">
                {idx}H
             </span>
             {/* Tooltip */}
             <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-bg-tertiary border border-border rounded text-[9px] font-bold text-white whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                Score: {(val * 100).toFixed(1)}% | {idx}:00
             </div>
          </div>
        ))}
      </div>

      <div className="flex justify-between items-center text-[10px] font-black uppercase text-text-muted mt-2">
         <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded bg-red" />
            <span>Short</span>
         </div>
         <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded bg-bg-tertiary border border-border" />
            <span>Neutral</span>
         </div>
         <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded bg-green" />
            <span>Long</span>
         </div>
      </div>
    </div>
  );
};

const getHeatmapColor = (val) => {
  if (val > 0.1) return `rgba(0, 212, 170, ${Math.min(val + 0.2, 1)})`;
  if (val < -0.1) return `rgba(255, 71, 87, ${Math.min(Math.abs(val) + 0.2, 1)})`;
  return 'rgba(26, 35, 50, 0.4)'; // Neutral tertiary
};

export default SignalHeatmap;
