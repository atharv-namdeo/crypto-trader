import React from 'react';

const Slider = ({ value, min, max, step, onChange, label }) => {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex justify-between items-center">
        <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-widest">{label}</span>
        <span className="font-mono text-xs text-text-primary">{value}</span>
      </div>
      <input 
        type="range" 
        min={min} 
        max={max} 
        step={step} 
        value={value} 
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-1 bg-bg-tertiary rounded-full appearance-none cursor-pointer accent-accent-primary"
      />
    </div>
  );
};

export default Slider;
