import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Command, LayoutDashboard, Zap, Shield, LineChart, Activity, Settings, List } from 'lucide-react';

const CommandPalette = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  const actions = [
    { id: 'dash', title: 'Go to Dashboard', icon: LayoutDashboard, path: '/', shortcut: 'D' },
    { id: 'trade', title: 'Open Trading Terminal', icon: Zap, path: '/trading', shortcut: 'T' },
    { id: 'perf', title: 'Strategy Performance', icon: Activity, path: '/strategies', shortcut: 'P' },
    { id: 'risk', title: 'Risk Management', icon: Shield, path: '/risk', shortcut: 'R' },
    { id: 'back', title: 'Run Backtest', icon: LineChart, path: '/backtester', shortcut: 'B' },
    { id: 'logs', title: 'System Logs', icon: List, path: '/logs', shortcut: 'L' },
    { id: 'sets', title: 'Settings', icon: Settings, path: '/settings', shortcut: 'S' },
  ];

  const filteredActions = query === '' 
    ? actions 
    : actions.filter(a => a.title.toLowerCase().includes(query.toLowerCase()));

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      setIsOpen(prev => !prev);
    }
    if (e.key === 'Escape') {
      setIsOpen(false);
    }
  }, []);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const runAction = (path: string) => {
    navigate(path);
    setIsOpen(false);
    setQuery('');
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsOpen(false)}
            className="fixed inset-0 bg-[#000000aa] backdrop-blur-sm z-[999]"
          />
          <motion.div 
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-xl bg-bg-secondary border border-border rounded-2xl shadow-2xl z-[1000] overflow-hidden"
          >
            <div className="flex items-center px-5 py-4 border-b border-border">
              <Search className="text-text-tertiary mr-3" size={20} />
              <input 
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Type a command or search..."
                className="bg-transparent border-none text-text-primary placeholder:text-text-tertiary focus:outline-none w-full text-lg font-medium"
              />
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded border border-border bg-bg-tertiary text-[10px] font-bold text-text-tertiary uppercase">
                <Command size={10} /> Esc
              </div>
            </div>

            <div className="max-h-[400px] overflow-y-auto p-2 no-scrollbar">
              {filteredActions.length > 0 ? filteredActions.map((action) => (
                <button 
                  key={action.id}
                  onClick={() => runAction(action.path)}
                  className="w-full flex items-center justify-between px-4 py-3 rounded-xl hover:bg-bg-tertiary/50 group transition-all"
                >
                  <div className="flex items-center gap-4">
                    <div className="p-2 rounded-lg bg-bg-secondary border border-border group-hover:border-accent-primary transition-all">
                      <action.icon size={18} className="text-text-tertiary group-hover:text-accent-primary transition-colors" />
                    </div>
                    <span className="font-bold text-text-primary text-sm">{action.title}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[10px] font-black text-text-tertiary opacity-40 group-hover:opacity-100 uppercase tracking-widest">
                    {action.shortcut}
                  </div>
                </button>
              )) : (
                <div className="py-12 text-center opacity-40">
                  <p className="text-xs font-bold uppercase tracking-widest leading-relaxed">No matching commands<br/>found for "{query}"</p>
                </div>
              )}
            </div>

            <div className="px-5 py-3 border-t border-border bg-bg-primary flex items-center justify-between">
              <div className="flex items-center gap-4 text-[10px] font-bold text-text-tertiary uppercase tracking-tighter">
                <span className="flex items-center gap-1 italic"><Command size={10} /> + K</span>
                <span>Search Everything</span>
              </div>
              <span className="text-[10px] font-black text-accent-primary tracking-widest uppercase italic">Quant Engine V8.0</span>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default CommandPalette;
