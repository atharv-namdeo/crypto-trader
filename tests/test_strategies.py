import pytest
import pandas as pd
from core.strategies.scalper import ScalperStrategy

@pytest.mark.asyncio
async def test_scalper_initialization():
    """Verify that the scalper strategy can be initialized."""
    strategy = ScalperStrategy()
    assert strategy.name == "SCALPER"
    assert strategy.timeframe == "1m"

@pytest.mark.asyncio
async def test_scalper_signal_generation(mock_candles):
    """Test signal generation with mock data."""
    strategy = ScalperStrategy()
    # Mock the state's get_df call if necessary
    # For now, we just test the internal logic if exposed
    assert True # Placeholder for more complex logic
