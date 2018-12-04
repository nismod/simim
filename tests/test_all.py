""" Test harness """

# Disable "Line too long"
# pylint: disable=C0301

import numpy as np
import pandas as pd
from unittest import TestCase

from pysal.contrib.spint.gravity import Gravity
from pysal.contrib.spint.gravity import Attraction
from pysal.contrib.spint.gravity import Doubly

# test methods only run if prefixed with "test"
class Test(TestCase):
  """ Test harness """

  # GB dataset of population, households and inter-LAD distances
  dataset = pd.read_csv("tests/data/test2011.csv.gz")

  def test_dataset(self):
    self.assertTrue(len(Test.dataset) == 378*377)

  def test_gravity(self):

    model = "pow"
    print("model: " + model)
    gravity = Gravity(Test.dataset.MIGRATIONS.values, Test.dataset.PEOPLE.values, Test.dataset.HOUSEHOLDS.values, Test.dataset.DISTANCE.values, model)
    #print(gravity.params)
    # TODO this formula is wrong?
    k = gravity.params[0]
    mu = gravity.params[1]
    alpha = gravity.params[2]
    beta = gravity.params[3]
    if model == "pow":
      est_unc = (np.exp(k) * Test.dataset.PEOPLE ** mu * Test.dataset.HOUSEHOLDS ** alpha * Test.dataset.DISTANCE ** beta).values
    else:
      est_unc = (np.exp(k) * Test.dataset.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * np.exp(Test.dataset.DISTANCE * beta)).values

    self.assertTrue(np.mean(est_unc - gravity.yhat) < 2e-16)
    self.assertTrue(np.sqrt(np.mean((est_unc - gravity.yhat)**2)) < 1e-13)
    # 1.4330978320718025e-16
    # 7.559644320891063e-14


if __name__ == "__main__":
  unittest.main()