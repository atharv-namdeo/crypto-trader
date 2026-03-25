import React from 'react';
import { motion } from 'framer-motion';

interface HeatmapCell {
  day: number;
  hour: number;
  value: number; // 0 to 1
  count: number;
}

interface SignalHeatmapProps {
  data: HeatmapCell[];
}

const SignalHeatmap: React.FC<SignalHeatmapProps> = ({ data }) => {
  const days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
  const hours = Array.from({ length: 24 }, (_, i) => i);

  // Group data by day and hour for easy lookups
  const dataMap = data.reduce((acc, cell) => {
    acc[`${cell.day}-${cell.hour}`] = cell;
    return acc;
  }, {} as Record<string, HeatmapCell>);

  const getColor = (value: number) => {
    if (value === 0) return 'bg-bg-tertiary/20';
    if (value < 0.25) return 'bg-accent-primary/20';
    if (value < 0.5) return 'bg-accent-primary/40';
    if (value < 0.75) return 'bg-accent-primary/70';
    return 'bg-accent-primary';
  };

  return (
    <div className="flex flex-col gap-4 overflow-x-auto no-scrollbar pb-2">
      <div className="flex gap-1.5 ml-8 mb-1">
        {hours.map(h => (
          <div key={h} className="w-3 text-[7px] font-bold text-text-tertiary text-center uppercase tracking-tighter">
            {h % 4 === 0 ? `${h}h` : ''}
          </div>
        ))}
      </div>

      {days.map((day, dIdx) => (
        <div key={day} className="flex items-center gap-1.5">
          <span className="w-6 text-[8px] font-black text-text-tertiary opacity-60 tracking-tighter mr-1">{day}</span>
          <div className="flex gap-1">
            {hours.map(h => {
              const cell = dataMap[`${dIdx}-${h}`] || { value: 0, count: 0 };
              return (
                <motion.div 
                  key={h}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: (dIdx * 24 + h) * 0.001 }}
                  className={`w-3 h-3 rounded-[1px] transition-all cursor-crosshair hover:ring-1 hover:ring-text-primary/30 relative group ${getColor(cell.value)}`}
                >
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-bg-primary border border-border rounded text-[8px] font-bold text-text-primary whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-20 pointer-events-none shadow-xl">
                    {day} {h}:00 — Accuracy: {(cell.value * 100).toFixed(1)}% ({cell.count} sigs)
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};

export default SignalHeatmap;
