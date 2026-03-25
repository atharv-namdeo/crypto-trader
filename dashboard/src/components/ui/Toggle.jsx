import React from 'react';

const Toggle = ({ active, onChange, label }) => {
  return (
    <div className="flex items-center justify-between gap-4">
      {label && <span className="text-xs font-bold text-text-secondary uppercase">{label}</span>}
      <div 
        onClick={() => onChange(!active)}
        className={`w-10 h-5 rounded-full cursor-pointer transition-all duration-200 relative ${active ? 'bg-accent-success' : 'bg-bg-tertiary border border-border'}`}
      >
        <div className={`w-3.5 h-3.5 rounded-full absolute top-[2px] transition-all duration-200 ${active ? 'bg-white left-[22px]' : 'bg-text-tertiary left-[3px]'}`}></div>
      </div>
    </div>
  );
};

export default Toggle;
