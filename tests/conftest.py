import pytest
import asyncio
from unittest.mock import MagicMock
import pandas as pd

@pytest.fixture
def mock_state():
    state = MagicMock()
    state.get = MagicMock(return_value=asyncio.Future())
    state.get.return_value.set_result(None)
    return state

@pytest.fixture
def mock_candles():
    return pd.DataFrame({
        'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='1min'),
        'open': [100.0] * 100,
        'high': [105.0] * 100,
        'low': [95.0] * 100,
        'close': [102.0] * 100,
        'volume': [1000.0] * 100
    })
