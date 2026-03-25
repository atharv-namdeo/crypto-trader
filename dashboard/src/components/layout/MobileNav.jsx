import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, TrendingUp, Zap, BarChart3, Settings } from 'lucide-react';

const MobileNav = () => {
  const items = [
    { name: 'Home', path: '/', icon: LayoutDashboard },
    { name: 'Trade', path: '/trading', icon: TrendingUp },
    { name: 'Signals', path: '/signals', icon: Zap },
    { name: 'Port', path: '/portfolio', icon: BarChart3 },
    { name: 'Config', path: '/settings', icon: Settings },
  ];

  return (
    <nav className="mobile-nav fixed bottom-0 left-0 right-0 h-16 bg-secondary border-t border-border flex items-center justify-around px-2 z-50 md:hidden">
      {items.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          className={({ isActive }) => `
            flex flex-col items-center gap-1 p-2 rounded-lg transition-all duration-200
            ${isActive ? 'text-accent-primary' : 'text-text-secondary'}
          `}
        >
          <item.icon size={20} />
          <span className="text-[10px] font-bold uppercase tracking-tighter">{item.name}</span>
        </NavLink>
      ))}
    </nav>
  );
};

export default MobileNav;
