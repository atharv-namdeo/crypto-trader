import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

import TopBar from './components/layout/TopBar';
import Sidebar from './components/layout/Sidebar';
import MobileNav from './components/layout/MobileNav';
import { SocketProvider } from './context/SocketContext';

// Real Pages
import Dashboard from './components/pages/Dashboard';
import Trading from './components/pages/Trading';
import Signals from './components/pages/Signals';
import Portfolio from './components/pages/Portfolio';
import Settings from './components/pages/Settings';
import Logs from './components/pages/Logs';

// Temporary components for missing routes
const Alerts = () => <div className="p-6"><h1>Critical Alerts</h1><p className="text-text-tertiary">Real-time system notification center coming soon.</p></div>;
const Risk = () => <div className="p-6"><h1>Risk Management</h1><p className="text-text-tertiary">Centralized risk assessment and circuit breaker controls.</p></div>;
const Backtester = () => <div className="p-6"><h1>Backtesting Suite</h1><p className="text-text-tertiary">Strategy validation and historical data replay.</p></div>;

const App = () => {
  return (
    <SocketProvider>
      <Router>
        <div className="app-container min-h-screen bg-bg-primary text-text-primary flex flex-col font-sans selection:bg-accent-primary/30">
          <Toaster 
            position="bottom-right"
            toastOptions={{
              style: {
                background: '#0f0f1a',
                color: '#f1f5f9',
                border: '1px solid #1e1e3a',
                fontSize: '12px',
                borderRadius: '4px',
                padding: '12px 16px'
              }
            }}
          />
          
          <TopBar />
          
          <div className="flex flex-1 overflow-hidden">
            <Sidebar />
            
            <main className="flex-1 md:ml-[220px] mt-[48px] overflow-y-auto overflow-x-hidden relative scroll-smooth bg-bg-primary">
              <div className="p-4 md:p-6 pb-24 md:pb-8 max-w-[1600px] mx-auto min-h-full">
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/trading" element={<Trading />} />
                  <Route path="/signals" element={<Signals />} />
                  <Route path="/portfolio" element={<Portfolio />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="/logs" element={<Logs />} />
                  <Route path="/alerts" element={<Alerts />} />
                  <Route path="/risk" element={<Risk />} />
                  <Route path="/backtester" element={<Backtester />} />
                </Routes>
              </div>
            </main>
            
            {/* Optional Right Panel could be injected here */}
          </div>

          <MobileNav />
        </div>
      </Router>
    </SocketProvider>
  );
};

export default App;
