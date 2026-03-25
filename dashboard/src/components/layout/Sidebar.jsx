import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  TrendingUp, 
  Zap, 
  BarChart3, 
  Briefcase, 
  ShieldAlert, 
  Layers, 
  Settings, 
  Terminal, 
  BellRing,
  Power
} from 'lucide-react';

const Sidebar = () => {
  const groups = [
    {
      label: 'OVERVIEW',
      items: [
        { name: 'Dashboard', path: '/', icon: LayoutDashboard },
        { name: 'Trading', path: '/trading', icon: TrendingUp },
      ]
    },
    {
      label: 'ENGINE',
      items: [
        { name: 'Strategies', path: '/strategies', icon: Layers },
        { name: 'Signals', path: '/signals', icon: Zap },
        { name: 'Portfolio', path: '/portfolio', icon: BarChart3 },
      ]
    },
    {
      label: 'CONTROLS',
      items: [
        { name: 'Risk Mgmt', path: '/risk', icon: ShieldAlert },
        { name: 'Backtester', path: '/backtester', icon: Briefcase },
        { name: 'Settings', path: '/settings', icon: Settings },
      ]
    },
    {
      label: 'SYSTEM',
      items: [
        { name: 'Logs', path: '/logs', icon: Terminal },
        { name: 'Alerts', path: '/alerts', icon: BellRing },
      ]
    }
  ];

  return (
    <aside className="sidebar fixed left-0 top-[48px] w-[220px] h-[calc(100vh-48px)] bg-bg-secondary border-r border-border flex flex-col p-4 z-40">
      <div className="flex-1 overflow-y-auto no-scrollbar">
        {groups.map((group, idx) => (
          <div key={idx} className="mb-6">
            <h3 className="text-[10px] font-bold text-text-tertiary mb-3 px-3 tracking-widest">{group.label}</h3>
            {group.items.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `
                  flex items-center gap-3 px-3 py-2 rounded-md transition-all duration-200 mb-1
                  ${isActive 
                    ? 'bg-accent-primary/10 text-accent-primary border border-accent-primary/20' 
                    : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary border border-transparent'}
                `}
              >
                <item.icon size={18} />
                <span className="text-[13px] font-medium">{item.name}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </div>

      <div className="mt-auto pt-4 border-t border-border">
        <div className="status-card bg-bg-tertiary p-3 rounded-md border border-border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-bold text-text-secondary uppercase tracking-tight">System Status</span>
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-accent-success' : 'bg-accent-danger'} animate-pulse`}></div>
          </div>
          <div className="flex items-center gap-2 mb-1">
             <span className="bg-accent-warning/10 text-accent-warning text-[10px] px-1.5 py-0.5 rounded border border-accent-warning/20 font-bold uppercase">Paper</span>
             <span className="text-[11px] font-mono text-text-tertiary uppercase tracking-tighter">v7.5 Engine @ IST</span>
          </div>
          <div className="text-[11px] text-text-secondary font-mono flex items-center justify-between">
            <span>Uptime:</span>
            <span>4h 23m</span>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
