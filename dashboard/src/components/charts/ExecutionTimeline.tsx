import React from 'react';
import { motion } from 'framer-motion';
import { Target, Zap, CheckCircle2, AlertCircle, Clock } from 'lucide-react';

interface TradeStep {
  type: 'SIGNAL' | 'ORDER' | 'FILL' | 'EXECUTION' | 'COMPLETION';
  title: string;
  desc: string;
  time: string;
  status: 'SUCCESS' | 'WARNING' | 'NEUTRAL';
  value?: string;
}

interface ExecutionTimelineProps {
  steps: TradeStep[];
}

const ExecutionTimeline: React.FC<ExecutionTimelineProps> = ({ steps }) => {
  return (
    <div className="flex flex-col gap-6 relative">
      <div className="absolute left-[15px] top-6 bottom-4 w-px bg-border/40"></div>
      
      {steps.map((step, idx) => (
        <motion.div 
          key={idx}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: idx * 0.1 }}
          className="relative pl-10 group"
        >
          {/* Connector Dot */}
          <div className={`absolute left-0 top-1.5 w-8 h-8 rounded-full bg-bg-primary border-2 flex items-center justify-center z-10 transition-all shadow-lg
            ${step.status === 'SUCCESS' ? 'border-accent-success' : step.status === 'WARNING' ? 'border-accent-danger' : 'border-border'}
          `}>
            {step.type === 'SIGNAL' && <Zap size={14} className={step.status === 'SUCCESS' ? 'text-accent-success' : 'text-accent-primary'} />}
            {step.type === 'ORDER' && <Target size={14} className="text-text-tertiary" />}
            {step.type === 'FILL' && <CheckCircle2 size={14} className="text-accent-success" />}
            {step.type === 'EXECUTION' && <Activity size={14} className="text-accent-primary" />}
            {step.type === 'COMPLETION' && <Clock size={14} className="text-text-primary" />}
          </div>

          <div className="bg-bg-tertiary/20 border border-border/40 rounded-xl p-4 hover:border-border transition-all hover:bg-bg-tertiary/40">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-[12px] font-bold text-text-primary uppercase tracking-tight">{step.title}</h4>
              <span className="text-[9px] font-mono font-bold text-text-tertiary opacity-60 tracking-tighter">{step.time}</span>
            </div>
            
            <p className="text-[11px] text-text-secondary font-medium leading-relaxed">{step.desc}</p>
            
            {step.value && (
              <div className="mt-2.5 pt-2.5 border-t border-border/30 flex items-center justify-between">
                <span className="text-[9px] font-bold text-text-tertiary uppercase tracking-widest">Detail</span>
                <span className="text-xs font-mono font-bold text-text-primary">{step.value}</span>
              </div>
            )}
          </div>
        </motion.div>
      ))}
    </div>
  );
};

// Internal Activity icon as fallback
const Activity = ({ size, className }: { size: number, className: string }) => (
  <svg 
    width={size} 
    height={size} 
    viewBox="0 0 24 24" 
    fill="none" 
    stroke="currentColor" 
    strokeWidth="2" 
    strokeLinecap="round" 
    strokeLinejoin="round" 
    className={className}
  >
    <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
  </svg>
);

export default ExecutionTimeline;
