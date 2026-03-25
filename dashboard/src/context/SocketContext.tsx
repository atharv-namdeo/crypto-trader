import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import toast from 'react-hot-toast';

export interface EngineData {
  market: Record<string, { price: number; change: number; high?: number; low?: number }>;
  strategies: Record<string, { 
    status: string; 
    daily_pnl: number; 
    total_pnl: number; 
    win_rate: number;
    trades_24h: number;
    avg_win: number;
    avg_loss: number;
    profit_factor: number;
    sharpe: number;
    max_drawdown: number;
    active_positions: number;
    allocated: number;
    last_trade?: string;
  }>;
  portfolio: { 
    total_value: number; 
    daily_pnl: number; 
    daily_change_pct: number;
    sharpe: number; 
    drawdown: number; 
    win_rate: number; 
    profit_factor: number; 
    sentiment: string;
  };
  positions: any[];
  orders: any[];
  trades: any[];
  logs: any[];
  equity_history: any[];
  signals: any[];
  latest_candles: any[];
  signal_heatmap: any[];
  status: string;
}

interface SocketContextType {
  data: EngineData;
  connected: boolean;
  socket: WebSocket | null;
}

const SocketContext = createContext<SocketContextType | undefined>(undefined);

export const SocketProvider = ({ children }: { children: ReactNode }) => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [data, setData] = useState<EngineData>({
    market: {},
    strategies: {},
    portfolio: { 
      total_value: 12450.32, 
      daily_pnl: 312.45, 
      daily_change_pct: 2.5,
      sharpe: 1.85, 
      drawdown: 0, 
      win_rate: 65, 
      profit_factor: 1.87, 
      sentiment: 'NEUTRAL' 
    },
    positions: [],
    orders: [],
    trades: [],
    logs: [],
    equity_history: [],
    signals: [],
    latest_candles: [],
    signal_heatmap: [],
    status: 'INITIALIZING'
  });
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host;
    const wsUrl = import.meta.env.VITE_WS_URL || `${protocol}//${host}/ws`;

    console.log(`🔌 Connecting to WebSocket: ${wsUrl}`);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('✅ WebSocket Connected');
      setConnected(true);
      setSocket(ws);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'engine_update') {
          setData(prev => {
            const incoming = message.data || {};
            
            // Deep merge essential objects to avoid losing fields or corrupting primitives
            return {
              ...prev,
              ...incoming,
              portfolio: {
                ...prev.portfolio,
                ...(incoming.portfolio || {})
              },
              market: {
                ...prev.market,
                ...(incoming.market || {})
              },
              strategies: {
                ...prev.strategies,
                ...(incoming.strategies || {})
              }
            };
          });
        } else if (message.type === 'TRADE_EXECUTED') {
          toast.success(`${message.data.side} ${message.data.symbol} at $${message.data.price}`, {
            icon: '🚀',
            duration: 5000
          });
        }
      } catch (err) {
        console.error('❌ WS Message Parsing Error:', err);
      }
    };

    ws.onclose = () => {
      console.log('🛑 WebSocket Disconnected');
      setConnected(false);
      setSocket(null);
    };

    ws.onerror = (err) => {
      console.error('❌ WebSocket Error:', err);
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <SocketContext.Provider value={{ data, connected, socket }}>
      {children}
    </SocketContext.Provider>
  );
};

export const useSocket = () => {
  const context = useContext(SocketContext);
  if (!context) {
    throw new Error('useSocket must be used within a SocketProvider');
  }
  return context;
};
