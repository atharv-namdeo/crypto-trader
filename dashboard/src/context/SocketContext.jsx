import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';

const SocketContext = createContext(null);

export const SocketProvider = ({ children }) => {
  const [socket, setSocket] = useState(null);
  const [data, setData] = useState({
    market: {},
    strategies: {},
    portfolio: { value: 0, sharpe: 0, drawdown: 0, win_rate: 0, profit_factor: 0, sentiment: 'NEUTRAL' },
    positions: [],
    orders: [],
    trades: [],
    logs: [],
    equity_history: [],
    signals: [],
    latest_candles: [],
    signal_heatmap: []
  });
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    // Determine WS URL based on current environment
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host;
    
    // Prioritize environment variable, fallback to current host
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
          setData(prev => ({
            ...prev,
            ...message.data
          }));
        } else if (message.type === 'TRADE_EXECUTED') {
          toast.success(`${message.data.side} ${message.data.symbol} at $${message.data.price}`, {
            icon: '🚀',
            duration: 5000
          });
        } else if (message.type === 'ML_UPDATE') {
          // Could update a specific slice of state if needed
        }
      } catch (err) {
        console.error('❌ WS Message Parsing Error:', err);
      }
    };

    ws.onclose = () => {
      console.log('🛑 WebSocket Disconnected');
      setConnected(false);
      setSocket(null);
      // Attempt reconnect after 5 seconds
      setTimeout(() => {
        setConnected(false);
      }, 5000);
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
