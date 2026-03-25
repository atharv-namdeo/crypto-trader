import React, { useState, useEffect, useRef } from 'react';
import { 
  Terminal, 
  Trash2, 
  Download, 
  Pause, 
  Play, 
  Search,
  Filter
} from 'lucide-react';
import { useSocket } from '../../context/SocketContext';

const Logs = () => {
  const { data } = useSocket();
  const [paused, setPaused] = useState(false);
  const [filter, setFilter] = useState('');
  const [displayLogs, setDisplayLogs] = useState([]);
  const bottomRef = useRef(null);

  // Sync logs from socket but allow pausing for inspection
  useEffect(() => {
    if (!paused && data?.logs) {
      setDisplayLogs(data.logs);
    }
  }, [data?.logs, paused]);

  // Scroll to bottom when new logs arrive
  useEffect(() => {
    if (!paused) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [displayLogs, paused]);

  const filteredLogs = displayLogs.filter(log => 
    log.message.toLowerCase().includes(filter.toLowerCase()) || 
    log.level.toLowerCase().includes(filter.toLowerCase())
  );

  const getLevelColor = (level) => {
    switch(level) {
      case 'ERROR': return 'text-accent-danger';
      case 'WARNING': return 'text-accent-warning';
      case 'SUCCESS': return 'text-accent-success';
      case 'INFO': return 'text-accent-primary';
      default: return 'text-text-tertiary';
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] animate-fade-in gap-4">
      {/* Log Toolbar */}
      <div className="card px-6 py-3 flex items-center justify-between bg-bg-secondary/80 backdrop-blur-sm sticky top-0 z-20">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3 pr-6 border-r border-border">
            <Terminal size={18} className="text-accent-primary" />
            <h2 className="text-sm font-bold uppercase tracking-widest text-text-primary">System Terminal</h2>
          </div>
          <div className="relative group">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-tertiary group-focus-within:text-accent-primary transition-colors" size={14} />
            <input 
              type="text" 
              placeholder="Filter logs (source, level, msg)..." 
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="bg-bg-tertiary border border-border rounded-[4px] py-1.5 pl-9 pr-4 text-[11px] font-bold text-text-secondary w-[300px] outline-none focus:border-accent-primary transition-all" 
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button 
            onClick={() => setPaused(!paused)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-[4px] text-[11px] font-bold uppercase transition-all ${paused ? 'bg-accent-warning text-white' : 'hover:bg-bg-tertiary text-text-secondary'}`}
          >
            {paused ? <Play size={14} /> : <Pause size={14} />}
            {paused ? 'Resume' : 'Pause'}
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 hover:bg-bg-tertiary text-text-secondary rounded-[4px] text-[11px] font-bold uppercase transition-all">
            <Download size={14} />
            Export
          </button>
          <button 
            onClick={() => setDisplayLogs([])}
            className="flex items-center gap-2 px-3 py-1.5 hover:bg-accent-danger/10 hover:text-accent-danger text-text-secondary rounded-[4px] text-[11px] font-bold uppercase transition-all"
          >
            <Trash2 size={14} />
            Clear
          </button>
        </div>
      </div>

      {/* Terminal Content */}
      <div className="card flex-1 bg-bg-primary overflow-hidden flex flex-col font-mono text-[12px] border-border/60">
        <div className="flex-1 overflow-y-auto p-6 scroll-smooth">
          {filteredLogs.length > 0 ? filteredLogs.map((log, i) => (
            <div key={i} className="flex gap-4 mb-2 group hover:bg-bg-tertiary/10 rounded px-2 -ml-2 transition-colors">
              <span className="text-text-tertiary shrink-0 select-none">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
              <span className={`w-16 font-black shrink-0 ${getLevelColor(log.level)}`}>{log.level}</span>
              <span className="text-text-secondary group-hover:text-text-primary"><span className="text-accent-purple">[{log.source}]</span> {log.message}</span>
            </div>
          )) : (
            <div className="h-full flex flex-col items-center justify-center text-text-tertiary animate-pulse">
              <Terminal size={48} className="mb-4 opacity-10" />
              <p className="uppercase tracking-[0.2em] font-black text-xs">Waiting for system pipe...</p>
            </div>
          )}
          <div ref={bottomRef} h-0 />
        </div>
        
        {/* Terminal Footer */}
        <div className="h-8 bg-bg-tertiary/30 border-t border-border px-4 flex items-center justify-between">
           <div className="flex gap-4">
              <span className="text-[10px] text-text-tertiary uppercase font-bold tracking-tighter">Connection: <span className="text-accent-success">CONNECTED</span></span>
              <span className="text-[10px] text-text-tertiary uppercase font-bold tracking-tighter">Buffer: <span className="text-accent-primary">{displayLogs.length} LINES</span></span>
           </div>
           <div className="text-[10px] text-text-tertiary uppercase font-bold tracking-tighter italic">Live Quant Engine v7.5 Diagnostics System</div>
        </div>
      </div>
    </div>
  );
};

export default Logs;
