import React, { useMemo } from 'react';
import { 
  AreaChart, 
  Area, 
  ResponsiveContainer,
  YAxis
} from 'recharts';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface MetricSparklineProps {
  title: string;
  value: string | number;
  change: number;
  data: { value: number }[];
  color?: string;
  prefix?: string;
}

const MetricSparkline: React.FC<MetricSparklineProps> = ({ 
  title, 
  value, 
  change, 
  data, 
  color = '#3b82f6',
  prefix = '$'
}) => {
  const isPositive = Number(change) >= 0;
  
  // Ensure value is safe to render
  const displayValue = useMemo(() => {
    if (typeof value === 'number') {
      return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    if (typeof value === 'string') return value;
    return JSON.stringify(value || '0.00');
  }, [value]);

  return (
    <div className="bg-bg-secondary border border-border rounded-xl p-4 flex flex-col gap-3 hover:border-border-bright transition-all group overflow-hidden relative">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-black text-text-tertiary uppercase tracking-[0.15em] opacity-80 group-hover:opacity-100 transition-opacity whitespace-nowrap">{title}</span>
        <div className={`p-1 rounded-md bg-${isPositive ? 'accent-success' : 'accent-danger'}/10`}>
          {isPositive ? <TrendingUp size={12} className="text-accent-success" /> : <TrendingDown size={12} className="text-accent-danger" />}
        </div>
      </div>
      
      <div className="flex items-baseline gap-1">
        <span className="text-xl font-mono font-bold tracking-tighter text-text-primary">
          {prefix}{displayValue}
        </span>
      </div>

      <div className="h-[40px] w-full mt-1">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id={`gradient-${title.replace(/\s+/g, '-')}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.3}/>
                <stop offset="95%" stopColor={color} stopOpacity={0}/>
              </linearGradient>
            </defs>
            <YAxis hide domain={['dataMin', 'dataMax']} />
            <Area 
              type="monotone" 
              dataKey="value" 
              stroke={color} 
              strokeWidth={2}
              fillOpacity={1} 
              fill={`url(#gradient-${title.replace(/\s+/g, '-')})`}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default MetricSparkline;
