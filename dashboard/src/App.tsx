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
import StrategyPerf from './components/pages/StrategyPerf';
import Risk from './components/pages/Risk';
import Backtester from './components/pages/Backtester';
import CommandPalette from './components/layout/CommandPalette';

class ErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean, error: any}> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }
  componentDidCatch(error: any, errorInfo: any) {
    console.error("ErrorBoundary caught an error", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '40px', background: '#0a0a0f', color: '#ef4444', minHeight: '100vh', fontFamily: 'monospace' }}>
          <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '16px' }}>🚨 Quant Engine Runtime Crash</h1>
          <div style={{ background: '#16161e', padding: '20px', borderRadius: '8px', border: '1px solid #1e1e2e', color: '#f8fafc' }}>
            <p style={{ marginBottom: '10px', fontWeight: 'bold' }}>Error Details:</p>
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: '12px', color: '#fb7185' }}>
              {this.state.error?.stack || this.state.error?.toString()}
            </pre>
          </div>
          <button 
            onClick={() => window.location.reload()}
            style={{ marginTop: '20px', background: '#3b82f6', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
          >
            Hot Reload / Refresh
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const App = () => {
  return (
    <Router>
      <ErrorBoundary>
        <SocketProvider>
          <CommandPalette />
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
              
              <main className="flex-1 lg:ml-[240px] mt-[56px] overflow-y-auto overflow-x-hidden relative scroll-smooth bg-bg-primary transition-all duration-300">
                <div className="p-4 md:p-8 pb-24 md:pb-12 max-w-[1800px] mx-auto min-h-full">
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/trading" element={<Trading />} />
                    <Route path="/portfolio" element={<Portfolio />} />
                    <Route path="/strategies" element={<StrategyPerf />} />
                    <Route path="/signals" element={<Signals />} />
                    <Route path="/backtester" element={<Backtester />} />
                    <Route path="/risk" element={<Risk />} />
                    <Route path="/logs" element={<Logs />} />
                    <Route path="/settings" element={<Settings />} />
                  </Routes>
                </div>
              </main>
            </div>

            <MobileNav />
          </div>
        </SocketProvider>
      </ErrorBoundary>
    </Router>
  );
};

export default App;
