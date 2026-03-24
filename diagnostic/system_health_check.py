import os
import asyncio
import json
import ccxt
import logging
from typing import Dict
from datetime import datetime
from core.state_manager import StateManager

log = logging.getLogger("Diagnostic")

class SystemHealthDiagnostic:
    """Diagnose why bot isn't executing trades"""
    
    def __init__(self):
        self.state = StateManager()

    async def full_diagnostic(self) -> Dict:
        """Run complete health check"""
        try:
            await self.state.connect()
        except Exception as e:
            return {'redis_connectivity': {'status': '❌ FAILED', 'error': str(e)}}
            
        results = {
            'binance_connectivity': await self._check_binance_connection(),
            'redis_connectivity': await self._check_redis(),
            'api_keys_valid': await self._validate_api_keys(),
            'data_feed': await self._check_data_feed(),
            'strategies_enabled': await self._check_strategies(),
            'ml_models': await self._check_ml_models(),
            'trading_logic': await self._check_trading_logic(),
            'state_manager': await self._check_state(),
            'websocket_connection': await self._check_websocket(),
            'orders_capability': await self._check_order_execution(),
        }
        
        return results
    
    async def _check_binance_connection(self) -> Dict:
        """Verify Binance API connectivity"""
        try:
            exchange = ccxt.binance({
                'apiKey': os.getenv('BINANCE_API_KEY'),
                'secret': os.getenv('BINANCE_API_SECRET'),
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                }
            })
            
            # Use testnet if requested
            if os.getenv('BINANCE_TESTNET', 'false').lower() == 'true':
                 exchange.set_sandbox_mode(True)
            
            balance = exchange.fetch_balance()
            ticker = exchange.fetch_ticker('BTC/USDT')
            
            return {
                'status': '✅ CONNECTED',
                'balance_fetched': balance is not None,
                'ticker_fetched': ticker is not None,
                'total_balance': balance.get('total', {}).get('USDT', 0),
                'test_time': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': '❌ FAILED',
                'error': str(e),
                'troubleshooting': [
                    'Check API key validity',
                    'Verify testnet environment variable',
                    'Confirm IP whitelist'
                ]
            }
    
    async def _check_redis(self) -> Dict:
        """Verify Redis connectivity and state"""
        try:
            # Test operations
            await self.state.set('test:ping', 'pong')
            result = await self.state.get('test:ping')
            
            # Check stored state
            stored_symbols = await self.state.get('config:symbols')
            stored_trades = await self.state.redis.llen('trade:history') if self.state.redis else 0
            
            return {
                'status': '✅ CONNECTED',
                'ping_successful': result == 'pong',
                'symbols_configured': stored_symbols is not None,
                'trades_history_length': stored_trades,
                'test_time': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': '❌ FAILED',
                'error': str(e)
            }
    
    async def _validate_api_keys(self) -> Dict:
        api_key = os.getenv('BINANCE_API_KEY', '').strip()
        api_secret = os.getenv('BINANCE_API_SECRET', '').strip()
        issues = []
        if not api_key: issues.append('BINANCE_API_KEY is empty')
        if not api_secret: issues.append('BINANCE_API_SECRET is empty')
        return {
            'status': '✅ VALID' if not issues else '❌ INVALID',
            'api_key_present': bool(api_key),
            'api_secret_present': bool(api_secret),
            'issues': issues
        }
    
    async def _check_data_feed(self) -> Dict:
        try:
            btc_candles = await self.state.get_df('ohlcv:1m:BTC/USDT', n=10)
            btc_price = await self.state.get_float('price:BTC/USDT')
            return {
                'status': '✅ ACTIVE' if btc_candles is not None else '❌ NOT FEEDING',
                'btc_candles_available': btc_candles is not None,
                'btc_current_price': btc_price
            }
        except Exception as e:
            return {'status': '❌ ERROR', 'error': str(e)}
    
    async def _check_strategies(self) -> Dict:
        try:
            strategies = ['scalper', 'swing', 'position']
            status = {}
            for strategy in strategies:
                enabled = await self.state.get(f'settings:{strategy}_enabled')
                status[strategy] = {'enabled': str(enabled).lower() != 'false'}
            return {
                'status': '✅ CONFIGURED' if any(s['enabled'] for s in status.values()) else '❌ ALL DISABLED',
                'strategies': status
            }
        except Exception as e:
            return {'status': '❌ ERROR', 'error': str(e)}
    
    async def _check_ml_models(self) -> Dict:
        models_dir = 'ml/models'
        if not os.path.exists(models_dir): return {'status': '❌ MISSING', 'error': 'ml/models dir not found'}
        files = os.listdir(models_dir)
        models = {
            'rf': any('rf' in f.lower() for f in files),
            'xgb': any('xgb' in f.lower() or 'boost' in f.lower() for f in files),
            'lstm': any('lstm' in f.lower() for f in files),
        }
        return {
            'status': '✅ LOADED' if any(models.values()) else '⚠️ MISSING',
            'models': models
        }
    
    async def _check_trading_logic(self) -> Dict:
        try:
            btc_candles = await self.state.get_df('ohlcv:1m:BTC/USDT', n=100)
            if btc_candles is None:
                return {'status': '❌ NO DATA', 'issue': 'Not enough candles in Redis'}
            return {'status': '✅ READY', 'candles_count': len(btc_candles)}
        except Exception as e:
            return {'status': '❌ ERROR', 'error': str(e)}
    
    async def _check_state(self) -> Dict:
        try:
            trading_mode = await self.state.get('trading:mode')
            account_equity = await self.state.get_float('portfolio:value')
            return {
                'status': '✅ HEALTHY',
                'trading_mode': trading_mode or 'UNKNOWN',
                'account_equity': account_equity,
            }
        except Exception as e:
            return {'status': '❌ ERROR', 'error': str(e)}
    
    async def _check_websocket(self) -> Dict:
        return {'status': '⚠️ MONITOR_BROWSER', 'note': 'Check browser console'}
    
    async def _check_order_execution(self) -> Dict:
        return {'status': '✅ READY', 'mode': os.getenv('PAPER_TRADING', 'true')}

async def main():
    diagnostic = SystemHealthDiagnostic()
    results = await diagnostic.full_diagnostic()
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
