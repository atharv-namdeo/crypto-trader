import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import { Brain } from 'lucide-react';

const FuzzyRadar = ({ fuzzyScores = {} }) => {
  const data = [
    { subject: 'RSI', A: fuzzyScores.rsi || 50, fullMark: 100 },
    { subject: 'VWAP Dev', A: Math.abs(fuzzyScores.vwap || 0) * 10, fullMark: 100 },
    { subject: 'Volume', A: (fuzzyScores.vol || 1) * 20, fullMark: 100 },
    { subject: 'ADX', A: (fuzzyScores.adx || 20) * 2, fullMark: 100 },
    { subject: 'Momentum', A: (fuzzyScores.long || 0) * 100, fullMark: 100 },
    { subject: 'Sentiment', A: (fuzzyScores.short || 0) * 100, fullMark: 100 },
  ];

  return (
    <div className="card p-6 flex flex-col items-center h-full">
      <div className="w-full flex justify-between items-center mb-6">
        <h3 className="text-sm font-bold flex items-center gap-2 uppercase tracking-tight text-text-primary">
          <Brain size={16} className="text-accent-primary" />
          Fuzzy Signal Radar
        </h3>
        <span className="px-2 py-0.5 rounded-[2px] bg-accent-success/10 text-accent-success text-[10px] font-bold border border-accent-success/20 uppercase tracking-widest">LIVE</span>
      </div>
      
      <div className="w-full flex-1 min-h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
            <PolarGrid stroke="#1e1e3a" />
            <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 10, fontWeight: 600 }} />
            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
            <Radar
              name="Market Score"
              dataKey="A"
              stroke="#3b82f6"
              fill="#3b82f6"
              fillOpacity={0.2}
              strokeWidth={2}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      
      <div className="mt-4 grid grid-cols-2 gap-8 w-full border-t border-border pt-6">
        <div className="text-center">
          <p className="text-[10px] font-bold text-text-tertiary uppercase mb-1">Ensemble Long</p>
          <p className="text-xl font-bold text-accent-success mono tracking-tight">{( (fuzzyScores.long || 0) * 100).toFixed(1)}%</p>
        </div>
        <div className="text-center border-l border-border">
          <p className="text-[10px] font-bold text-text-tertiary uppercase mb-1">Ensemble Short</p>
          <p className="text-xl font-bold text-accent-danger mono tracking-tight">{( (fuzzyScores.short || 0) * 100).toFixed(1)}%</p>
        </div>
      </div>
    </div>
  );
};

export default FuzzyRadar;
