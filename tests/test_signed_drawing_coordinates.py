import unittest
from agentrader.chart.drawings.coordinates import coordinate_text
from agentrader.chart.drawings.service import geometry,DrawingError
from agentrader.chart.chart_precision import decimal_text,PrecisionError
from agentrader.chart.drawings.calculations import normalized,query,CalculationBlocked

class SignedCoordinates(unittest.TestCase):
 def test_signed_drawing_domain_is_separate_from_market_prices(self):
  for value,expected in [('-1.250','-1.25'),('-0.00','0'),('0','0'),('-1e-8','-0.00000001')]:self.assertEqual(coordinate_text(value),expected)
  for value in ['NaN','Infinity','-+1','--1','1_000',' 1']:
   with self.assertRaises(ValueError):coordinate_text(value)
  with self.assertRaises(PrecisionError):decimal_text('-1',positive=True)
 def test_persisted_geometry_accepts_zero_negative_coordinates_but_queries_fail_closed(self):
  g=dict(kind='trend',symbol='BTCUSDT',price_source='LAST_PRICE',anchors=[dict(time=1800000000,price='0'),dict(time=1800000900,price='-10')],label='signed')
  self.assertEqual(geometry(g)['anchors'][1]['price'],'-10');self.assertEqual(normalized(g)['anchors'][0]['price'],'0')
  with self.assertRaises(CalculationBlocked):query(g,'priceAt',time=1800000900,times=[1800000000,1800000900],interval='15m')
