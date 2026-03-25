import React, { useState, useEffect } from 'react';
import Toggle from '../ui/Toggle';
import Slider from '../ui/Slider';
import Badge from '../ui/Badge';
import toast from 'react-hot-toast';

const Settings = () => {
  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState({
    scalper_enabled: true,
    scalper_threshold: 0.45,
    swing_enabled: true,
    swing_threshold: 0.55,
    position_enabled: false,
    position_threshold: 0.65
  });

  const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/settings`)
      .then(res => res.json())
      .then(json => {
        if (json.data) {
          // Convert string "true"/"false" to boolean if necessary
          const normalized = {};
          Object.entries(json.data).forEach(([k, v]) => {
            if (v === 'true') normalized[k] = true;
            else if (v === 'false') normalized[k] = false;
            else normalized[k] = v;
          });
          setSettings(prev => ({ ...prev, ...normalized }));
        }
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to fetch settings:', err);
        setLoading(false);
      });
  }, []);

  const handleSave = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (response.ok) {
        toast.success('Configuration saved to Quant Engine');
      } else {
        toast.error('Failed to save configuration');
      }
    } catch (err) {
      toast.error('Network error during save');
    }
  };

  if (loading) return <div className="p-12 text-center text-text-tertiary font-bold animate-pulse uppercase tracking-[0.2em]">Synchronizing Engine State...</div>;

  return (
    <div className="flex flex-col gap-6 animate-fade-in max-w-5xl mx-auto pb-12">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-text-primary tracking-tight">Configuration & Control</h2>
        <div className="flex gap-2">
            <button className="px-5 py-1.5 rounded bg-bg-tertiary border border-border text-xs font-bold text-text-secondary hover:text-white transition-all">Discard</button>
            <button 
                onClick={handleSave}
                className="px-5 py-1.5 rounded bg-accent-primary border border-accent-primary text-xs font-bold text-white hover:brightness-110 shadow-lg shadow-accent-primary/20 transition-all"
            >
                Save Configuration
            </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Strategy Controls */}
        <div className="card p-6 flex flex-col gap-6">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <h3 className="text-sm font-bold text-text-primary uppercase tracking-tight">Strategy Flow</h3>
            <Badge variant="primary">Active</Badge>
          </div>
          
          {['scalper', 'swing', 'position'].map(s => (
            <div key={s} className="p-4 rounded-card bg-bg-tertiary border border-border flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-text-primary">{s.toUpperCase()} ENGINE</span>
                <Toggle 
                  active={settings[`${s}_enabled`]} 
                  onChange={(val) => setSettings({...settings, [`${s}_enabled`]: val})} 
                />
              </div>
              <Slider 
                label="Entry Confidence Threshold" 
                min={0} max={1} step={0.01} 
                value={settings[`${s}_threshold`]} 
                onChange={(val) => setSettings({...settings, [`${s}_threshold`]: val})}
              />
            </div>
          ))}
        </div>

        {/* Risk Management */}
        <div className="flex flex-col gap-6">
          <div className="card p-6 flex flex-col gap-6">
            <div className="flex items-center justify-between border-b border-border pb-4">
              <h3 className="text-sm font-bold text-text-primary uppercase tracking-tight">Risk Constraints</h3>
              <Badge variant="danger">Enabled</Badge>
            </div>
            
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <div className="flex flex-col">
                        <span className="text-xs font-bold text-text-secondary uppercase">Max Daily Loss</span>
                        <span className="text-[10px] text-text-tertiary uppercase">Hard stop threshold</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-text-tertiary font-mono text-xs">$</span>
                        <input type="number" defaultValue={500} className="w-24 bg-bg-tertiary border-border py-1 font-mono text-sm font-bold text-accent-danger" />
                    </div>
                </div>

                <div className="pt-4 mt-4 border-t border-border border-dashed">
                    <button className="w-full py-3 rounded bg-accent-danger/20 text-accent-danger border border-accent-danger/30 font-black uppercase tracking-[0.2em] hover:bg-accent-danger hover:text-white transition-all">
                        Emergency STOP
                    </button>
                </div>
            </div>
          </div>

          <div className="card p-6 bg-accent-primary/5 border-dashed border-accent-primary/20">
              <h4 className="text-[11px] font-bold text-accent-primary uppercase mb-2">Automated Risk Guardian</h4>
              <p className="text-[11px] text-text-secondary leading-relaxed">
                  The Risk Guardian is monitoring margin levels and system health in the background. If volatility spikes > 15% in 5m, all strategies will pause automatically.
              </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
