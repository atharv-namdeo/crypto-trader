import React from 'react';

const Badge = ({ children, variant = 'default', className = '' }) => {
  const variants = {
    default: 'bg-bg-tertiary text-text-secondary border-border',
    success: 'bg-accent-success/10 text-accent-success border-accent-success/20',
    danger: 'bg-accent-danger/10 text-accent-danger border-accent-danger/20',
    warning: 'bg-accent-warning/10 text-accent-warning border-accent-warning/20',
    primary: 'bg-accent-primary/10 text-accent-primary border-accent-primary/20',
    purple: 'bg-accent-purple/10 text-accent-purple border-accent-purple/20',
    cyan: 'bg-accent-cyan/10 text-accent-cyan border-accent-cyan/20',
    orange: 'bg-accent-orange/10 text-accent-orange border-accent-orange/20',
  };

  return (
    <span className={`
      inline-flex items-center px-1.5 py-0.5 rounded-[2px] text-[10px] font-bold uppercase tracking-wider border
      ${variants[variant] || variants.default}
      ${className}
    `}>
      {children}
    </span>
  );
};

export default Badge;
