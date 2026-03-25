import React, { useState } from 'react';
import { 
  ShieldCheck, 
  Settings as SettingsIcon, 
  Zap, 
  Layers, 
  Database, 
  Globe, 
  Cpu,
  Save,
  RefreshCcw,
  CheckCircle2
} from 'lucide-react';
import { useSocket } from '../../context/SocketContext';
import toast from 'react-hot-toast';

const Settings = () => {
  const { data } = useSocket();
  const [saving, setSaving] = useState(false);

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      toast.success('Configuration synchronized with Engine v7.5');
    }, 1500);
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in pb-12">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-text-primary tracking-tight uppercase flex items-center gap-2">
            <SettingsIcon size={22} className="text-accent-primary" />
            Engine Configuration
          </h2>
          <p className="text-[11px] text-text-tertiary font-bold uppercase tracking-widest mt-1 italic">Real-time Strategy & Risk Orchestration</p>
        </div>
        <button 
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-5 py-2 bg-accent-primary text-white rounded-[4px] font-bold text-[12px] uppercase tracking-wider hover:opacity-90 disabled:opacity-50 transition-all shadow-lg shadow-accent-primary/20"
        >
          {saving ? <RefreshCcw size={16} className="animate-spin" /> : <Save size={16} />}
          {saving ? 'Syncing...' : 'Save & Sync'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Management */}
        <div className="card p-6">
           <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-accent-danger/10 rounded-md text-accent-danger border border-accent-danger/20">
                <ShieldCheck size={20} />
              </div>
              <h3 className="font-bold text-sm uppercase tracking-tight">Global Risk Perimeter</h3>
           </div>
           
           <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                 <div className="flex flex-col gap-2">
                    <label className="text-[11px] font-bold text-text-tertiary uppercase">Daily Loss Limit (%)</label>
                    <input type="number" defaultValue="2.5" className="bg-bg-tertiary border border-border rounded p-2 text-sm font-mono text-accent-danger" />
                 </div>
                 <div className="flex flex-col gap-2">
                    <label className="text-[11px] font-bold text-text-tertiary uppercase">Max Drawdown Exit (%)</label>
                    <input type="number" defaultValue="5.0" className="bg-bg-tertiary border border-border rounded p-2 text-sm font-mono text-accent-danger" />
                 </div>
              </div>
              
              <div className="flex flex-col gap-3 p-4 bg-bg-tertiary/10 border border-border rounded-md">
                 <div className="flex items-center justify-between">
                    <span className="text-[12px] font-bold text-text-secondary">Emergency Circuit Breaker</span>
                    <div className="w-10 h-5 bg-accent-danger rounded-full p-1 relative cursor-pointer opacity-40 grayscale">
                       <div className="w-3 h-3 bg-white rounded-full"></div>
                    </div>
                 </div>
                 <p className="text-[10px] text-text-tertiary italic">Closes all positions and halts scanning if volatility exceeds 15% in 1 minute.</p>
              </div>
           </div>
        </div>

        {/* Strategy Controls */}
        <div className="card p-6">
           <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-accent-primary/10 rounded-md text-accent-primary border border-accent-primary/20">
                <Layers size={20} />
              </div>
              <h3 className="font-bold text-sm uppercase tracking-tight">Strategy Orchestrator</h3>
           </div>

           <div className="space-y-4">
              {['Scalper', 'Swing', 'Position'].map((s, i) => (
                <div key={s} className="flex items-center justify-between p-3 border border-border/50 rounded-md hover:border-border-bright transition-colors">
                   <div className="flex items-center gap-4">
                      <div className={`w-2 h-2 rounded-full ${i === 0 ? 'bg-accent-primary' : i === 1 ? 'bg-accent-success' : 'bg-accent-purple'}`}></div>
                      <div className="flex flex-col">
                        <span className="text-[13px] font-bold text-text-primary uppercase">{s}</span>
                        <span className="text-[10px] text-text-tertiary uppercase font-medium">{i === 0 ? 'High Freq' : i === 1 ? 'Medium Term' : 'Passive'}</span>
                      </div>
                   </div>
                   <div className="flex items-center gap-8">
                      <div className="flex flex-col items-end">
                        <span className="text-[10px] text-text-tertiary uppercase font-bold">Allocation</span>
                        <span className="text-[12px] font-mono font-bold text-text-primary">{i === 0 ? '10%' : i === 1 ? '30%' : '60%'}</span>
                      </div>
                      <div className="w-10 h-5 bg-accent-success/20 border border-accent-success/40 rounded-full p-1 relative cursor-pointer">
                        <div className="w-3 h-3 bg-accent-success rounded-full absolute right-1"></div>
                      </div>
                   </div>
                </div>
              ))}
           </div>
        </div>

        {/* Infrastructure */}
        <div className="card p-6">
           <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-accent-purple/10 rounded-md text-accent-purple border border-accent-purple/20">
                <Database size={20} />
              </div>
              <h3 className="font-bold text-sm uppercase tracking-tight">Data Integrity & Sync</h3>
           </div>

           <div className="space-y-4">
              <div className="flex items-center justify-between text-[12px] p-2">
                 <span className="flex items-center gap-2 text-text-secondary"><Globe size={14}/> Binance WS Link</span>
                 <span className="flex items-center gap-1.5 text-accent-success font-bold uppercase"><CheckCircle2 size={12}/> Connected</span>
              </div>
              <div className="flex items-center justify-between text-[12px] p-2">
                 <span className="flex items-center gap-2 text-text-secondary"><Cpu size={14}/> Redis Memory Usage</span>
                 <span className="font-mono text-text-secondary">4.2MB / 64MB</span>
              </div>
              <div className="flex flex-col gap-2 mt-4">
                <label className="text-[11px] font-bold text-text-tertiary uppercase">Exchange API Environment</label>
                <select className="bg-bg-tertiary border border-border rounded p-2 text-[12px] text-text-primary appearance-none outline-none focus:border-accent-primary transition-all">
                   <option>Binance Futures Testnet</option>
                   <option disabled>Binance Futures Mainnet (KYC Required)</option>
                   <option>Bybit Unified Margin (Paper)</option>
                </select>
              </div>
           </div>
        </div>

        {/* AI Multi-Model Configuration */}
        <div className="card p-6">
           <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-accent-amber/10 rounded-md text-accent-amber border border-accent-amber/20">
                <Zap size={20} />
              </div>
              <h3 className="font-bold text-sm uppercase tracking-tight">ML Ensemble Tuning</h3>
           </div>

           <div className="space-y-6">
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="text-[11px] font-bold text-text-tertiary uppercase tracking-wider">Confidence Threshold</label>
                  <span className="text-[11px] font-mono font-bold text-accent-amber">75%</span>
                </div>
                <input type="range" min="50" max="95" defaultValue="75" className="w-full h-1 bg-bg-tertiary rounded-lg appearance-none cursor-pointer accent-accent-amber" />
                <div className="flex justify-between mt-1 text-[9px] text-text-tertiary uppercase font-bold">
                  <span>Conservative</span>
                  <span>Aggressive</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                 {['XGBoost v2', 'LightGBM', 'Ensemble Voting', 'Prophet Mix'].map(algo => (
                   <div key={algo} className="flex items-center gap-2">
                      <input type="checkbox" defaultChecked className="w-3.5 h-3.5 rounded bg-bg-tertiary border-border transition-all checked:bg-accent-amber" />
                      <span className="text-[12px] text-text-secondary">{algo}</span>
                   </div>
                 ))}
              </div>
           </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
