""" Test harness """

# Disable "Line too long"
# pylint: disable=C0301

import numpy as np
import pandas as pd
from unittest import TestCase

from pysal.contrib.spint.gravity import Gravity
from pysal.contrib.spint.gravity import Attraction
from pysal.contrib.spint.gravity import Doubly

from simim.utils import r2, rmse
import simim.models as models

# test methods only run if prefixed with "test"
class Test(TestCase):
  """ Test harness """

  # GB dataset of population, households and inter-LAD distances
  dataset = pd.read_csv("tests/data/test2011.csv.gz")

  def test_stats(self):
    np.random.seed(0)
    x = np.random.normal(0,1,10000)
    y = np.random.normal(0,1,10000)

    # R2
    self.assertEqual(r2(x,x), 1.0)
    self.assertEqual(r2(x,-x), 1.0) # rho=-1 
    self.assertTrue(-0.0001 < r2(x,y) < 0.0001)
    # 
    rho = 0.5
    res = r2(x, rho * x + np.sqrt(1 - rho**2) * y)
    self.assertTrue(rho**2 - 0.015 < res < rho**2 + 0.015)

    z = np.zeros(10000)
    self.assertEqual(rmse(x,z), np.sqrt(np.mean(x*x)))
    self.assertEqual(rmse(x,x), 0.0)
    self.assertEqual(rmse(x,-x), np.sqrt(np.mean(4*x*x)))


  def test_dataset(self):
    self.assertTrue(len(Test.dataset) == 378*377)

  def test_gravity(self):
    for model_subtype in ["pow", "exp"]:
      gravity = models.Model("gravity", model_subtype, Test.dataset.MIGRATIONS.values, 
                                                       Test.dataset.PEOPLE.values, 
                                                       Test.dataset.HOUSEHOLDS.values, 
                                                       Test.dataset.DISTANCE.values)
      self.assertTrue(rmse(gravity(Test.dataset.PEOPLE.values, Test.dataset.HOUSEHOLDS.values), gravity.impl.yhat) < 1e-13)
      Test.dataset["HH_CHANGED"] = Test.dataset.HOUSEHOLDS
      Test.dataset.loc[Test.dataset.D_GEOGRAPHY_CODE == "E07000178", "HH_CHANGED"] = Test.dataset.loc[Test.dataset.D_GEOGRAPHY_CODE == "E07000178", "HOUSEHOLDS"] + 300000 
      self.assertTrue(rmse(gravity(Test.dataset.PEOPLE.values, Test.dataset.HH_CHANGED.values), gravity.impl.yhat) > 1.0)

if __name__ == "__main__":
  unittest.main()