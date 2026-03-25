import { NavLink, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  TrendingUp, 
  Zap, 
  Briefcase, 
  ShieldAlert, 
  Layers, 
  Settings, 
  Terminal, 
  PieChart,
  Activity,
  Cpu
} from 'lucide-react';
import { useSocket } from '../../context/SocketContext';

const Sidebar = () => {
  const { data, connected } = useSocket();
  const safeNumber = (val: any) => typeof val === 'number' ? val : parseFloat(String(val || 0)) || 0;
  const safeScalar = (val: any) => (typeof val === 'string' || typeof val === 'number') ? val : '';
  
  const location = useLocation();
  const groups = [
    {
      label: 'Portfolio & Overview',
      items: [
        { name: 'Dashboard', path: '/', icon: LayoutDashboard },
        { name: 'Trading Activity', path: '/trading', icon: TrendingUp },
        { name: 'Portfolio Analysis', path: '/portfolio', icon: PieChart },
      ]
    },
    {
      label: 'Algorithmic Engine',
      items: [
        { name: 'Strategy Perf', path: '/strategies', icon: Layers },
        { name: 'Signals & Decisions', path: '/signals', icon: Zap },
        { name: 'Backtester Hub', path: '/backtester', icon: Briefcase },
      ]
    },
    {
      label: 'Security & Risk',
      items: [
        { name: 'Risk Management', path: '/risk', icon: ShieldAlert },
        { name: 'System Logs', path: '/logs', icon: Terminal },
        { name: 'Settings', path: '/settings', icon: Settings },
      ]
    }
  ];

  return (
    <aside className="sidebar fixed left-0 top-[56px] w-[240px] h-[calc(100vh-56px)] bg-bg-secondary border-r border-border flex flex-col p-4 z-40 transition-all duration-300">
      <div className="flex-1 overflow-y-auto no-scrollbar py-2">
        {groups.map((group, idx) => (
          <div key={idx} className="mb-8">
            <h3 className="text-[10px] font-bold text-text-tertiary mb-4 px-3 tracking-[0.2em] uppercase opacity-70">
              {group.label}
            </h3>
            {group.items.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
              >
                {({ isActive }: { isActive: boolean }) => (
                  <div className={`
                    group flex items-center justify-between px-3 py-2.5 rounded-lg transition-all duration-300 mb-1.5
                    ${isActive 
                      ? 'bg-accent-primary/10 text-accent-primary shadow-[inset_0_0_12px_rgba(var(--accent-primary-rgb),0.05)]' 
                      : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'}
                  `}>
                    <div className="flex items-center gap-3">
                      <item.icon size={18} className={`transition-colors ${isActive ? 'text-accent-primary' : 'text-text-tertiary group-hover:text-text-secondary'}`} />
                      <span className={`text-[13px] font-bold tracking-tight ${isActive ? 'text-text-primary' : ''}`}>
                        {item.name}
                      </span>
                    </div>
                    {isActive && (
                      <div className="w-1.5 h-1.5 bg-accent-primary rounded-full shadow-[0_0_8px_rgba(var(--accent-primary-rgb),0.5)]"></div>
                    )}
                  </div>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </div>

      <div className="mt-auto pt-6 border-t border-border/50">
        <div className="bg-bg-tertiary/50 backdrop-blur-sm p-4 rounded-xl border border-border/50 hover:border-border-bright transition-all group">
          <div className="flex items-center justify-between mb-3">
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-tighter">Engine Core</span>
              <span className="text-[11px] font-bold text-text-primary group-hover:text-accent-primary transition-colors">Bybit demo-node-01</span>
            </div>
            <div className={`w-2.5 h-2.5 rounded-full ${connected ? 'bg-accent-success shadow-[0_0_10px_rgba(34,197,94,0.5)]' : 'bg-accent-danger shadow-[0_0_10px_rgba(239,68,68,0.5)]'} animate-pulse`}></div>
          </div>
          
          <div className="space-y-2">
             <div className="flex items-center justify-between text-[10px] text-text-tertiary">
               <span className="flex items-center gap-1.5"><Activity size={10} /> Latency</span>
               <span className="font-mono text-text-secondary">24ms</span>
             </div>
             <div className="flex items-center justify-between text-[10px] text-text-tertiary">
               <span className="flex items-center gap-1.5"><Cpu size={10} /> Load</span>
               <span className="font-mono text-text-secondary">1.2%</span>
             </div>
          </div>
        </div>
        
        <div className="mt-4 flex items-center justify-center">
           <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-widest opacity-50 italic">Quant Engine Pro Suite v8.0</span>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
