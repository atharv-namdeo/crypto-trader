import { useSocket } from '../context/SocketContext';

export const usePortfolioStats = () => {
  const { data, connected } = useSocket();
  
  const safeNumber = (val: any) => typeof val === 'number' ? val : parseFloat(String(val || 0)) || 0;

  return {
    portfolio: {
      total_value: safeNumber(data?.portfolio?.total_value ?? 0),
      daily_change_pct: safeNumber(data?.portfolio?.daily_change_pct ?? 0),
      daily_pnl: safeNumber(data?.portfolio?.daily_pnl ?? 0),
      sharpe: safeNumber(data?.portfolio?.sharpe ?? 0),
      drawdown: safeNumber(data?.portfolio?.drawdown ?? 0),
      win_rate: safeNumber(data?.portfolio?.win_rate ?? 0),
      trades: safeNumber(data?.portfolio?.trades ?? 0),
      sentiment: data?.portfolio?.sentiment || 'NEUTRAL',
    },
    portfolioValue: safeNumber(data?.portfolio?.total_value ?? 0),
    portfolioChange: safeNumber(data?.portfolio?.daily_change_pct ?? 0),
    dailyPnl: safeNumber(data?.portfolio?.daily_pnl ?? 0),
    sentimentScore: Math.min(100, Math.max(0, (data?.portfolio?.sentiment === 'BULL' ? 75 : data?.portfolio?.sentiment === 'BEAR' ? 25 : 50))),
    connected,
    data
  };
};
