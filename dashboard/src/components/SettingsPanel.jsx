import React, { useState } from 'react';
import { Settings, Save, RefreshCcw, Bell } from 'lucide-react';

const SettingsPanel = ({ settings, onUpdate }) => {
  const [localSettings, setLocalSettings] = useState(settings);

  const toggle = (key) => {
    const newVal = localSettings[key] === 'true' ? 'false' : 'true';
    const updated = { ...localSettings, [key]: newVal };
    setLocalSettings(updated);
    onUpdate(key, newVal);
  };

  const handleSlider = (key, val) => {
      const updated = { ...localSettings, [key]: parseFloat(val) };
      setLocalSettings(updated);
      onUpdate(key, parseFloat(val));
  };

  const strategies = [
    { id: 'scalper', label: 'Scalper Engine', desc: '1m high-speed capture' },
    { id: 'swing', label: 'Swing Engine', desc: '1h trend following' },
    { id: 'position', label: 'Position Engine', desc: '4h macro alignment' },
  ];

  return (
    <div className="card p-6 h-full flex flex-col gap-8 overflow-y-auto">
      <div className="flex justify-between items-center bg-bg-secondary p-3 -m-6 mb-2 border-b border-border">
          <h3 className="text-sm font-black flex items-center gap-2 uppercase tracking-widest text-[#7a8ba5]">
            <Settings size={16} className="text-accent" />
            Bot Control Center
          </h3>
          <div className="flex gap-2">
            <button className="btn-ghost p-1.5"><Bell size={16}/></button>
            <button className="btn-ghost p-1.5"><RefreshCcw size={16}/></button>
          </div>
      </div>

      <div className="space-y-8 mt-2">
        {strategies.map(s => (
          <div key={s.id} className="flex flex-col gap-4 border-b border-border/40 pb-6 last:border-0 last:pb-0">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm font-black text-text-primary">{s.label}</p>
                <p className="text-[10px] text-text-muted font-extrabold uppercase">{s.desc}</p>
              </div>
              <div 
                className={`toggle-track ${localSettings[`${s.id}_enabled`] === 'true' ? 'active' : ''}`}
                onClick={() => toggle(`${s.id}_enabled`)}
              >
                <div className="toggle-thumb" />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-[10px] font-black uppercase text-text-muted">
                <span>Confidence Threshold</span>
                <span className="text-accent">{Math.round(localSettings[`${s.id}_threshold`] * 100)}%</span>
              </div>
              <input 
                type="range" 
                min="0.3" 
                max="0.8" 
                step="0.01" 
                value={localSettings[`${s.id}_threshold`] || 0.5}
                onChange={(e) => handleSlider(`${s.id}_threshold`, e.target.value)}
                className="w-full h-1 bg-border rounded-lg appearance-none cursor-pointer accent-accent"
              />
              <div className="flex justify-between text-[8px] font-bold text-text-muted uppercase">
                <span>Aggressive (30%)</span>
                <span>Conservative (80%)</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-auto space-y-4">
          <div className="p-4 bg-accent-dim rounded-xl border border-accent/20">
              <p className="text-[10px] font-black uppercase text-accent mb-1">Portfolio Risk Capacity</p>
              <div className="progress-bar w-full">
                  <div className="progress-fill bg-accent" style={{ width: '65%' }}></div>
              </div>
              <div className="flex justify-between mt-1 text-[8px] font-bold text-accent italic">
                  <span>65% Utilized</span>
                  <span>$350 Free Capital</span>
              </div>
          </div>
          
          <button className="btn-primary w-full flex items-center justify-center gap-2 py-3">
              <Save size={16} />
              COMMIT CHANGES
          </button>
      </div>
    </div>
  );
};

export default SettingsPanel;
