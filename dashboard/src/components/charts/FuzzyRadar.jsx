import React from 'react';
import { 
  Radar, 
  RadarChart, 
  PolarGrid, 
  PolarAngleAxis, 
  PolarRadiusAxis, 
  ResponsiveContainer,
  Legend
} from 'recharts';

const FuzzyRadar = ({ data }) => {
  const defaultData = [
    { subject: 'RSI', A: 120, B: 110, fullMark: 150 },
    { subject: 'VWAP', A: 98, B: 130, fullMark: 150 },
    { subject: 'Volume', A: 86, B: 130, fullMark: 150 },
    { subject: 'ADX', A: 99, B: 100, fullMark: 150 },
    { subject: 'Divergence', A: 85, B: 90, fullMark: 150 },
    { subject: 'Momentum', A: 65, B: 85, fullMark: 150 },
  ];

  return (
    <div className="h-[300px] w-full mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data || defaultData}>
          <PolarGrid stroke="#1e1e3a" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 10, fontWeight: 'bold' }} />
          <PolarRadiusAxis hide />
          <Radar
            name="Long Strength"
            dataKey="A"
            stroke="#10b981"
            fill="#10b981"
            fillOpacity={0.3}
          />
          <Radar
            name="Short Strength"
            dataKey="B"
            stroke="#ef4444"
            fill="#ef4444"
            fillOpacity={0.3}
          />
          <Legend wrapperStyle={{ fontSize: '10px', color: '#94a3b8', paddingTop: '10px' }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default FuzzyRadar;
