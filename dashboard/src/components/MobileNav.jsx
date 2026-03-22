import React from 'react';
import { LayoutDashboard, Brain, Activity, Briefcase, Settings } from 'lucide-react';

const MobileNav = ({ activeTab, setTab }) => {
  const links = [
    { id: 'dashboard', label: 'Dash', icon: LayoutDashboard },
    { id: 'trading', label: 'Trade', icon: Activity },
    { id: 'signals', label: 'Signals', icon: Brain },
    { id: 'portfolio', label: 'Assets', icon: Briefcase },
    { id: 'settings', label: 'Set', icon: Settings },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-bg-secondary border-t border-border flex items-center justify-around md:hidden h-16 z-50 px-2 slide-up-animation">
      {links.map(link => (
        <div 
          key={link.id}
          onClick={() => setTab(link.id)}
          className={`flex flex-col items-center gap-1 px-3 py-1 pb-2 transition-all duration-200 ${activeTab === link.id ? 'text-accent border-b-2 border-accent' : 'text-text-muted'}`}
        >
          <link.icon size={20} strokeWidth={activeTab === link.id ? 2.5 : 1.5} />
          <span className="text-[10px] font-black uppercase tracking-tight">{link.label}</span>
        </div>
      ))}
    </nav>
  );
};

export default MobileNav;
