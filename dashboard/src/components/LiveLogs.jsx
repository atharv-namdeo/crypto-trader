import React, { useState, useEffect, useRef } from 'react';
import { Terminal, Pause, Play, Trash2, Filter } from 'lucide-react';

const LiveLogs = ({ logs }) => {
  const [isPaused, setIsPaused] = useState(false);
  const [filter, setFilter] = useState('');
  const [displayLogs, setDisplayLogs] = useState([]);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (!isPaused) {
      const filtered = logs.filter(l => 
        l.msg.toLowerCase().includes(filter.toLowerCase()) || 
        l.name.toLowerCase().includes(filter.toLowerCase())
      );
      setDisplayLogs(filtered);
    }
  }, [logs, filter, isPaused]);

  useEffect(() => {
    if (scrollRef.current && !isPaused) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [displayLogs, isPaused]);

  return (
    <div className="card flex flex-col h-[400px] overflow-hidden">
      <div className="px-6 py-3 border-b border-border flex justify-between items-center bg-bg-secondary">
        <div className="flex items-center gap-2">
          <Terminal size={14} className="text-accent" />
          <h3 className="text-xs font-black uppercase tracking-widest text-[#7a8ba5]">Live System Logs</h3>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative group">
            <Filter size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-text-muted" />
            <input 
              type="text" 
              placeholder="FILTER..." 
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="bg-bg-tertiary border border-border rounded px-2 py-1 pl-7 text-[10px] font-black mono w-32 focus:w-48 transition-all outline-none text-text-primary"
            />
          </div>
          <button onClick={() => setIsPaused(!isPaused)} className="text-text-muted hover:text-accent transition-colors">
            {isPaused ? <Play size={16} /> : <Pause size={16} />}
          </button>
          <button onClick={() => setDisplayLogs([])} className="text-text-muted hover:text-red transition-colors">
            <Trash2 size={16} />
          </button>
        </div>
      </div>
      
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-1 bg-black/20 mono text-[11px]">
        {displayLogs.length === 0 ? (
          <div className="h-full flex items-center justify-center text-text-muted italic opacity-50">
            Awaiting engine activity...
          </div>
        ) : (
          displayLogs.map((log, idx) => (
            <div key={idx} className="flex gap-3 px-2 py-0.5 rounded hover:bg-bg-tertiary group">
              <span className="text-text-muted font-bold shrink-0">{log.time}</span>
              <span className={`font-black tracking-tighter shrink-0 w-12 text-center rounded ${getLogLevelClass(log.level)}`}>
                {log.level}
              </span>
              <span className="text-blue font-bold shrink-0 opacity-70">[{log.name}]</span>
              <span className="text-text-primary break-all">{log.msg}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

const getLogLevelClass = (level) => {
  switch (level) {
    case 'INFO': return 'bg-blue-dim text-blue';
    case 'WARNING': return 'bg-warning-dim text-warning';
    case 'ERROR': return 'bg-red-dim text-red';
    case 'CRITICAL': return 'bg-red text-white';
    default: return 'bg-bg-tertiary text-text-muted';
  }
};

export default LiveLogs;
