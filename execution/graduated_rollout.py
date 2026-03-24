import logging
import time
import json
from core.state_manager import StateManager

log = logging.getLogger("GraduatedRollout")

class GraduatedRollout:
    """
    Safely scale live trading capital over time.
    Starts with minimum position size, increases as bot proves itself.
    """
    
    PHASES = {
        'PHASE_1_MICRO': {
            'duration_days': 7,
            'position_size_pct': 1,    # 1% of capital per trade
            'max_concurrent_trades': 2,
            'description': 'Micro trades - validate execution'
        },
        'PHASE_2_MINI': {
            'duration_days': 14,
            'position_size_pct': 2,    # 2% of capital per trade
            'max_concurrent_trades': 3,
            'description': 'Mini trades - validate consistency'
        },
        'PHASE_3_STANDARD': {
            'duration_days': 30,
            'position_size_pct': 5,    # 5% of capital per trade
            'max_concurrent_trades': 4,
            'description': 'Standard trades - normal operation'
        },
        'PHASE_4_SCALED': {
            'duration_days': 60,
            'position_size_pct': 10,   # 10% of capital per trade
            'max_concurrent_trades': 6,
            'description': 'Scaled operation - full capacity'
        },
    }
    
    def __init__(self, state: StateManager, start_capital: float):
        self.state = state
        self.start_capital = start_capital
        self.phase_start_time = time.time()
        self.current_phase = 'PHASE_1_MICRO'
    
    async def get_position_size(self) -> float:
        """Get current max position size based on phase"""
        # Load persisted phase if exists
        saved_phase = await self.state.get('rollout:current_phase')
        if saved_phase:
            self.current_phase = saved_phase
            
        phase_config = self.PHASES[self.current_phase]
        
        # Check if time to advance phase
        start_ts = await self.state.get_float('rollout:phase_start_time') or self.phase_start_time
        elapsed_days = (time.time() - start_ts) / 86400
        
        if elapsed_days > phase_config['duration_days']:
            await self._advance_phase()
        
        return self.start_capital * (phase_config['position_size_pct'] / 100)
    
    async def _advance_phase(self):
        """Advance to next phase if conditions met"""
        current_idx = list(self.PHASES.keys()).index(self.current_phase)
        
        if current_idx < len(self.PHASES) - 1:
            # Check performance metrics
            if await self._phase_passed_checks():
                new_phase = list(self.PHASES.keys())[current_idx + 1]
                self.current_phase = new_phase
                now = time.time()
                await self.state.set('rollout:current_phase', new_phase)
                await self.state.set('rollout:phase_start_time', now)
                
                phase_config = self.PHASES[new_phase]
                log.info(f"✅ GRADUATED TO {new_phase}: {phase_config['description']}")
            else:
                log.warning(f"⚠️ Failed to advance phase - staying in {self.current_phase}")
    
    async def _phase_passed_checks(self) -> bool:
        """Check if current phase performance is acceptable"""
        trades_raw = await self.state.redis.lrange('trade:history', 0, -1)
        if len(trades_raw) < 5:
            return False
            
        pnls = [float(json.loads(t).get('pnl', 0)) for t in trades_raw]
        win_rate = sum(1 for p in pnls if p > 0) / len(pnls)
        avg_pnl = sum(pnls) / len(pnls)
        
        return win_rate > 0.45 and avg_pnl >= 0
    
    async def get_status_report(self) -> dict:
        """Get current rollout status for dashboard"""
        config = self.PHASES[self.current_phase]
        start_ts = await self.state.get_float('rollout:phase_start_time') or self.phase_start_time
        elapsed = (time.time() - start_ts) / 86400
        
        return {
            'current_phase': self.current_phase,
            'description': config['description'],
            'position_size_pct': config['position_size_pct'],
            'max_trades': config['max_concurrent_trades'],
            'days_elapsed': round(elapsed, 1),
            'days_required': config['duration_days']
        }
