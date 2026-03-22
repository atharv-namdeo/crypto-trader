import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import { Brain } from 'lucide-react';

const FuzzyRadar = ({ fuzzyScores }) => {
  // scores is { rsi, vwap, vol, adx, long, short }
  // We need to map this to Radar format
  const data = [
    { subject: 'RSI', A: fuzzyScores.rsi || 50, fullMark: 100 },
    { subject: 'VWAP Dev', A: Math.abs(fuzzyScores.vwap || 0) * 10, fullMark: 100 },
    { subject: 'Volume', A: (fuzzyScores.vol || 1) * 20, fullMark: 100 },
    { subject: 'ADX', A: (fuzzyScores.adx || 20) * 2, fullMark: 100 },
    { subject: 'Momentum', A: (fuzzyScores.long || 0) * 100, fullMark: 100 },
    { subject: 'Sentiment', A: (fuzzyScores.short || 0) * 100, fullMark: 100 },
  ];

  return (
    <div className="card p-6 flex flex-col items-center">
      <div className="w-full flex justify-between items-center mb-6">
        <h3 className="text-sm font-black flex items-center gap-2 uppercase tracking-widest text-[#7a8ba5]">
          <Brain size={16} className="text-accent" />
          Fuzzy Signal Radar (BTC)
        </h3>
        <span className="badge badge-green">LIVE</span>
      </div>
      
      <div className="w-full h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
            <PolarGrid stroke="#1e2b3d" />
            <PolarAngleAxis dataKey="subject" tick={{ fill: '#4a5a70', fontSize: 10, fontWeight: 800 }} />
            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
            <Radar
              name="Market Score"
              dataKey="A"
              stroke="#00d4aa"
              fill="#00d4aa"
              fillOpacity={0.2}
              strokeWidth={3}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      
      <div className="mt-4 grid grid-cols-2 gap-8 w-full">
        <div className="text-center">
          <p className="stat-label mb-1">Ensemble Long</p>
          <p className="text-xl font-black text-green mono">{(fuzzyScores.long * 100 || 0).toFixed(1)}%</p>
        </div>
        <div className="text-center">
          <p className="stat-label mb-1">Ensemble Short</p>
          <p className="text-xl font-black text-red mono">{(fuzzyScores.short * 100 || 0).toFixed(1)}%</p>
        </div>
      </div>
    </div>
  );
};

export default FuzzyRadar;
