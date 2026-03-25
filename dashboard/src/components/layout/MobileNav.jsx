import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  TrendingUp, 
  Zap, 
  BarChart3, 
  Terminal
} from 'lucide-react';

const MobileNav = () => {
  const items = [
    { name: 'Home', path: '/', icon: LayoutDashboard },
    { name: 'Trade', path: '/trading', icon: TrendingUp },
    { name: 'Signals', path: '/signals', icon: Zap },
    { name: 'Net', path: '/portfolio', icon: BarChart3 },
    { name: 'Logs', path: '/logs', icon: Terminal },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 h-[64px] bg-bg-secondary border-t border-border flex items-center justify-around px-2 z-50 md:hidden pb-safe">
      {items.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          className={({ isActive }) => `
            flex flex-col items-center justify-center gap-1 group
            ${isActive ? 'text-accent-primary' : 'text-text-tertiary'}
          `}
        >
          <div className={`p-1 rounded-md transition-all ${isActive ? 'bg-accent-primary/10' : 'group-hover:bg-bg-hover'}`}>
            <item.icon size={20} />
          </div>
          <span className="text-[10px] font-bold uppercase tracking-tight">{item.name}</span>
        </NavLink>
      ))}
    </nav>
  );
};

export default MobileNav;
