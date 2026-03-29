import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import toast from 'react-hot-toast';
import { rtdb } from '../firebase';
import { ref, onValue } from 'firebase/database';

export interface EngineData {
  market: Record<string, { price: number; change: number; high?: number; low?: number }>;
  strategies: Record<string, { 
    status: string; 
    daily_pnl: number; 
    pnl?: number;
    total_pnl: number; 
    win_rate: number;
    trades_24h: number;
    trades?: number;
    avg_win: number;
    avg_loss: number;
    profit_factor: number;
    sharpe: number;
    max_drawdown: number;
    active_positions: number;
    allocated: number;
    avg_hold: string;
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
    volatility: number;
    trades: number;
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
  exchange?: string;
  node?: string;
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
      total_value: 0, 
      daily_pnl: 0, 
      daily_change_pct: 0,
      sharpe: 0, 
      drawdown: 0, 
      win_rate: 0,
      profit_factor: 0,
      sentiment: 'NEUTRAL',
      volatility: 0,
      trades: 0
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
    const getWsUrl = () => {
      // 1. Explicit environment variable always wins (e.g. from Vercel/Railway env)
      if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;

      // 2. Local development fallback
      if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'ws://localhost:8000/ws';
      }

      // 3. Fallback to current host (assuming same-origin deployment)
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${protocol}//${window.location.host}/ws`;
    };

    const wsUrl = getWsUrl();

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
              status: incoming.status || prev.status,
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

  // --- FIREBASE REALTIME LISTENERS (Cloud Source of Truth) ---
  useEffect(() => {
    // Sync VITE_WS_URL status to connected for Firebase-only mode
    if (!connected && !socket) {
       console.log("☁️ Running in Cloud-Native (Firebase Only) mode");
       setConnected(true);
    }
    
    console.log("🔥 Initializing Firebase Realtime Listeners...");
    
    // 1. Market Prices
    const marketRef = ref(rtdb, 'market/prices');
    const unsubscribeMarket = onValue(marketRef, (snapshot) => {
      const val = snapshot.val();
      if (val) {
        setData(prev => ({
          ...prev,
          market: {
            ...prev.market,
            ...Object.fromEntries(
              Object.entries(val).map(([sym, data]: [string, any]) => [
                sym, 
                { 
                  price: data.current_price, 
                  change: 0, 
                  confidence: data.confidence || 0 
                }
              ])
            )
          }
        }));
      }
    });

    // 2. Aggregated Positions
    const posActiveRef = ref(rtdb, 'trading/positions_active');
    const unsubscribePosActive = onValue(posActiveRef, (snapshot) => {
      const val = snapshot.val();
      if (val) {
        setData(prev => ({
          ...prev,
          positions: Array.isArray(val) ? val : Object.values(val)
        }));
      }
    });

    // 3. Signals
    const signalRef = ref(rtdb, 'trading/signals');
    const unsubscribeSignals = onValue(signalRef, (snapshot) => {
      const val = snapshot.val();
      if (val) {
        setData(prev => ({
          ...prev,
          signals: Object.values(val)
        }));
      }
    });

    // 4. Status & Engine Meta
    const statusRef = ref(rtdb, 'status');
    const unsubscribeStatus = onValue(statusRef, (snapshot) => {
      const val = snapshot.val();
      if (val) {
        setData(prev => ({ 
          ...prev, 
          status: val.label || 'Operational',
          exchange: val.exchange || 'Binance Testnet'
        }));
      }
    });

    // 5. Portfolio Analytics
    const analyticsRef = ref(rtdb, 'analytics/performance/summary');
    const unsubscribeAnalytics = onValue(analyticsRef, (snapshot) => {
      const val = snapshot.val();
      if (val) {
        setData(prev => ({
          ...prev,
          portfolio: {
            ...prev.portfolio,
            ...val
          }
        }));
      }
    });

    // 6. Strategy Stats
    const stratRef = ref(rtdb, 'trading/strategies');
    const unsubscribeStrats = onValue(stratRef, (snapshot) => {
      const val = snapshot.val();
      if (val) {
        setData(prev => ({
          ...prev,
          strategies: {
            ...prev.strategies,
            ...val
          }
        }));
      }
    });

    // 7. Active Orders
    const ordersRef = ref(rtdb, 'trading/orders_active');
    const unsubscribeOrders = onValue(ordersRef, (snapshot) => {
      const val = snapshot.val();
      if (val) {
        setData(prev => ({
          ...prev,
          orders: Array.isArray(val) ? val : Object.values(val)
        }));
      }
    });

    // 8. Fuzzy Scores
    const fuzzyRef = ref(rtdb, 'market/fuzzy');
    const unsubscribeFuzzy = onValue(fuzzyRef, (snapshot) => {
      const val = snapshot.val();
      if (val) {
        setData(prev => {
          const newMarket = { ...prev.market };
          Object.entries(val).forEach(([sym, scores]: [string, any]) => {
            if (newMarket[sym]) {
              // @ts-ignore - fuzzy property expected by specific components
              newMarket[sym] = { ...newMarket[sym], fuzzy: scores };
            }
          });
          return { ...prev, market: newMarket };
        });
      }
    });

    return () => {
      unsubscribeMarket();
      unsubscribePosActive();
      unsubscribeSignals();
      unsubscribeStatus();
      unsubscribeAnalytics();
      unsubscribeStrats();
      unsubscribeOrders();
      unsubscribeFuzzy();
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
