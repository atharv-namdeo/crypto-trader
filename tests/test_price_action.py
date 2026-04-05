import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from core.strategies.price_action_engine import PriceActionZoneEngine, ZoneTradeFilter

class TestPriceAction(unittest.TestCase):
    def setUp(self):
        self.engine = PriceActionZoneEngine()
        self.filter = ZoneTradeFilter(self.engine)
        
        # Create dummy OHLCV data with clear pivot points
        data = {
            'timestamp': range(100),
            'open':  [100]*100,
            'high':  [110 if i % 10 == 0 else 105 for i in range(100)],
            'low':   [90 if i % 10 == 5 else 95 for i in range(100)],
            'close': [100]*100,
            'volume':[1000]*100
        }
        self.df = pd.DataFrame(data)

    def test_zone_detection(self):
        zones = self.engine.find_major_zones(self.df, window=100)
        
        # We expect a resistance zone near 110 and a support zone near 90
        has_resistance = any(abs(z - 110) < 1 for z in zones['resistance'])
        has_support = any(abs(z - 90) < 1 for z in zones['support'])
        
        self.assertTrue(has_resistance, f"Resistance near 110 not found: {zones['resistance']}")
        self.assertTrue(has_support, f"Support near 90 not found: {zones['support']}")

    def test_zone_validation(self):
        zones = self.engine.find_major_zones(self.df, window=100)
        fibs = {} # Empty fibs for simple test
        
        # Price at 90.1 should be valid for BUY (near support)
        valid_buy, score_buy = self.filter.validate_entry('BUY', 90.1, zones, fibs)
        self.assertTrue(valid_buy)
        self.assertGreater(score_buy, 0)
        
        # Price at 100 should NOT be valid (mid-range)
        valid_mid, score_mid = self.filter.validate_entry('BUY', 100, zones, fibs)
        self.assertFalse(valid_mid)
        self.assertEqual(score_mid, 0)

if __name__ == '__main__':
    unittest.main()
