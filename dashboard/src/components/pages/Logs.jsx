import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, Trash2, Search } from 'lucide-react';
import { useSocket } from '../../context/SocketContext';

const Logs = () => {
  const { data, connected } = useSocket();
  const [isLive, setIsLive] = useState(true);
  const [filter, setFilter] = useState('');
  const logEndRef = useRef(null);

  const logs = data?.logs || [];

  useEffect(() => {
    if (isLive && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, isLive]);

  const getLevelColor = (level) => {
    switch (level) {
      case 'SUCCESS': return 'text-accent-success';
      case 'ERROR': return 'text-accent-danger';
      case 'WARNING': return 'text-accent-warning';
      case 'INFO': return 'text-text-secondary';
      default: return 'text-text-secondary';
    }
  };

  const getCategoryColor = (cat) => {
    switch (cat?.toUpperCase()) {
      case 'SCALPER': return 'text-accent-cyan';
      case 'SWING': return 'text-accent-purple';
      case 'POSITION': return 'text-accent-orange';
      case 'ORDER': return 'text-accent-primary';
      default: return 'text-white';
    }
  };

  const filteredLogs = logs.filter(l => 
    l.msg?.toLowerCase().includes(filter.toLowerCase()) || 
    l.name?.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] animate-fade-in">
      {/* Controls Bar */}
      <div className="flex items-center justify-between gap-4 mb-4 p-3 bg-bg-secondary rounded-card border border-border">
          <div className="flex items-center gap-2">
            <button 
                onClick={() => setIsLive(!isLive)}
                className={`flex items-center gap-2 px-3 py-1 rounded text-[10px] font-bold uppercase tracking-widest transition-all ${isLive ? 'bg-accent-success/10 text-accent-success border border-accent-success/20' : 'bg-bg-tertiary text-text-tertiary border border-border'}`}
            >
                {isLive ? <Play size={12} fill="currentColor" /> : <Pause size={12} fill="currentColor" />}
                {isLive ? 'Live' : 'Paused'}
            </button>
            <button 
                className="flex items-center gap-2 px-3 py-1 rounded bg-bg-tertiary border border-border text-[10px] font-bold text-text-tertiary hover:text-accent-danger transition-all uppercase tracking-widest"
            >
                <Trash2 size={12} /> Clear
            </button>
          </div>

          <div className="flex-1 flex items-center bg-bg-primary rounded border border-border px-3 focus-within:border-accent-primary transition-all">
              <Search size={14} className="text-text-tertiary" />
              <input 
                type="text" 
                placeholder="Filter logs..." 
                className="bg-transparent border-none text-xs py-1.5 w-full focus:ring-0"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              />
          </div>
      </div>

      {/* Terminal Area */}
      <div className="flex-1 bg-[#050508] rounded-card border border-border overflow-y-auto font-mono text-[12px] p-4 custom-scrollbar">
        <div className="flex flex-col gap-1">
          {filteredLogs.map((log, i) => (
            <div key={i} className="flex gap-3 hover:bg-white/5 py-0.5 transition-colors">
              <span className="text-text-tertiary whitespace-nowrap">[{log.time}]</span>
              <span className={`font-bold whitespace-nowrap min-w-[80px] ${getCategoryColor(log.name)}`}>[{log.name}]</span>
              <span className={`font-bold whitespace-nowrap min-w-[70px] ${getLevelColor(log.level)}`}>{log.level}</span>
              <span className="text-text-primary break-all">{log.msg}</span>
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>
      
      <div className="mt-3 flex justify-between items-center px-2">
          <div className="text-[10px] text-text-tertiary uppercase font-bold tracking-widest">
              Showing {filteredLogs.length} lines | Status: {connected ? 'Streaming' : 'Searching...'}
          </div>
          <div className={`text-[10px] uppercase font-bold tracking-widest ${connected ? 'text-accent-success animate-pulse' : 'text-accent-danger'}`}>
              {connected ? '● Connected to Redis Stream' : '○ Disconnected'}
          </div>
      </div>
    </div>
  );
};

export default Logs;
