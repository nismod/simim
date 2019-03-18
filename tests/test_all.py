""" Test harness """

# Disable "Line too long"
# pylint: disable=C0301

import numpy as np
import pandas as pd
from unittest import TestCase

from simim.utils import r2, rmse
import simim.models as models

# test methods only run if prefixed with "test"
class Test(TestCase):
  """ Test harness """

  # GB dataset of population, households, jobs and inter-LAD distances
  dataset = pd.read_csv("tests/data/testdata.csv.gz").sort_values(["D_GEOGRAPHY_CODE", "O_GEOGRAPHY_CODE"])

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
    self.assertTrue(len(Test.dataset) == 378*378)

  # basic tests of model functionality
  def test_models(self):
    g = models.Model("gravity", "pow", Test.dataset, "MIGRATIONS", "PEOPLE", "HOUSEHOLDS", "DISTANCE")
    self.assertEqual(g.num_emit, 1)
    self.assertEqual(g.num_attr, 1)
    self.assertEqual(g.impl.params[0], g.k())
    self.assertEqual(g.impl.params[1:2], g.mu())
    self.assertEqual(g.impl.params[-2:-1], g.alpha())
    self.assertEqual(g.impl.params[-1], g.beta())

    g = models.Model("gravity", "pow", Test.dataset, "MIGRATIONS", "PEOPLE", ["HOUSEHOLDS", "JOBS"], "DISTANCE")
    self.assertEqual(g.num_emit, 1)
    self.assertEqual(g.num_attr, 2)
    self.assertEqual(g.impl.params[0], g.k())
    self.assertEqual(g.impl.params[1:2], g.mu())
    self.assertTrue(np.allclose(g.impl.params[-3:-1], g.alpha()))
    self.assertEqual(g.impl.params[-1], g.beta())

    g = models.Model("gravity", "pow", Test.dataset, "MIGRATIONS", ["PEOPLE", "JOBS"], "HOUSEHOLDS", "DISTANCE")
    self.assertEqual(g.num_emit, 2)
    self.assertEqual(g.num_attr, 1)
    self.assertEqual(g.impl.params[0], g.k())
    self.assertTrue(np.allclose(g.impl.params[1:3], g.mu()))
    self.assertEqual(g.impl.params[-2:-1], g.alpha())
    self.assertEqual(g.impl.params[-1], g.beta())

    p = models.Model("production", "pow", Test.dataset, "MIGRATIONS", "O_GEOGRAPHY_CODE", "HOUSEHOLDS", "DISTANCE")
    self.assertEqual(p.num_emit, 377)
    self.assertEqual(p.num_attr, 1)
    self.assertEqual(p.impl.params[0], p.k())
    self.assertTrue(np.allclose(p.impl.params[1:378], p.mu()))
    self.assertEqual(p.impl.params[-2:-1], p.alpha())
    self.assertEqual(p.impl.params[-1], p.beta())

    p = models.Model("production", "pow", Test.dataset, "MIGRATIONS", "O_GEOGRAPHY_CODE", ["HOUSEHOLDS", "JOBS"], "DISTANCE")
    self.assertEqual(p.num_emit, 377)
    self.assertEqual(p.num_attr, 2)
    self.assertEqual(p.impl.params[0], p.k())
    self.assertTrue(np.allclose(p.impl.params[1:378], p.mu()))
    self.assertTrue(np.allclose(p.impl.params[-3:-1], p.alpha()))
    self.assertEqual(p.impl.params[-1], p.beta())

    a = models.Model("attraction", "pow", Test.dataset, "MIGRATIONS", "PEOPLE", "D_GEOGRAPHY_CODE", "DISTANCE")
    self.assertEqual(a.num_emit, 1)
    self.assertEqual(a.num_attr, 377)
    self.assertEqual(a.impl.params[0], a.k())
    self.assertTrue(np.allclose(a.impl.params[-2:-1], a.mu()))
    self.assertTrue(np.allclose(a.impl.params[1:378], a.alpha()))
    self.assertEqual(a.impl.params[-1], a.beta())

    # model doesnt converge
    # a = models.Model("attraction", "pow", Test.dataset, "MIGRATIONS", ["PEOPLE", "JOBS"], "D_GEOGRAPHY_CODE", "DISTANCE")
    # print(a.impl.params)
    # self.assertEqual(a.num_emit, 2)
    # self.assertEqual(a.num_attr, 377)
    # self.assertEqual(a.impl.params[0], a.k())
    # self.assertTrue(np.allclose(a.impl.params[-3:-1], a.mu()))
    # self.assertTrue(np.allclose(a.impl.params[1:378], a.alpha()))
    # self.assertEqual(a.impl.params[-1], a.beta())


  def test_gravity(self):
    # single factor prod and attr
    for model_subtype in ["pow", "exp"]:
      gravity = models.Model("gravity", model_subtype, Test.dataset, "MIGRATIONS", "PEOPLE", "HOUSEHOLDS", "DISTANCE")
      self.assertTrue(rmse(gravity(Test.dataset.PEOPLE.values, Test.dataset.HOUSEHOLDS.values), gravity.impl.yhat) < 1e-10)
      Test.dataset["HH_CHANGED"] = Test.dataset.HOUSEHOLDS
      Test.dataset.loc[Test.dataset.D_GEOGRAPHY_CODE == "E07000178", "HH_CHANGED"] = Test.dataset.loc[Test.dataset.D_GEOGRAPHY_CODE == "E07000178", "HOUSEHOLDS"] + 300000 
      self.assertTrue(rmse(gravity(Test.dataset.PEOPLE.values, Test.dataset.HH_CHANGED.values), gravity.impl.yhat) > 1.0)

  def test_gravity2(self):
    # multi factor emission
    for model_subtype in ["pow", "exp"]:
      gravity = models.Model("gravity", model_subtype, Test.dataset, "MIGRATIONS", "PEOPLE", ["HOUSEHOLDS", "JOBS"], "DISTANCE")
      self.assertTrue(rmse(gravity(Test.dataset.PEOPLE.values, [Test.dataset.HOUSEHOLDS.values, Test.dataset.JOBS.values]), gravity.impl.yhat) < 1e-10)
    # multi factor attraction
    for model_subtype in ["pow", "exp"]:
      gravity = models.Model("gravity", model_subtype, Test.dataset, "MIGRATIONS", ["PEOPLE", "JOBS"], "HOUSEHOLDS", "DISTANCE")
      self.assertTrue(rmse(gravity([Test.dataset.PEOPLE.values, Test.dataset.JOBS.values], Test.dataset.HOUSEHOLDS.values), gravity.impl.yhat) < 1e-10)

  def test_production(self):
    # single factor attr
    for model_subtype in ["pow", "exp"]:
      production = models.Model("production", model_subtype, Test.dataset, "MIGRATIONS", "O_GEOGRAPHY_CODE", "HOUSEHOLDS", "DISTANCE")
      self.assertTrue(rmse(production(xd=Test.dataset.HOUSEHOLDS.values), production.impl.yhat) < 1e-10)
      Test.dataset["HH_CHANGED"] = Test.dataset.HOUSEHOLDS
      Test.dataset.loc[Test.dataset.D_GEOGRAPHY_CODE == "E07000178", "HH_CHANGED"] = Test.dataset.loc[Test.dataset.D_GEOGRAPHY_CODE == "E07000178", "HOUSEHOLDS"] + 300000 
      self.assertTrue(rmse(production(xd=Test.dataset.HH_CHANGED.values), production.impl.yhat) > 1.0)

  def test_production2(self):
    # single factor attr
    for model_subtype in ["pow", "exp"]:
      production = models.Model("production", model_subtype, Test.dataset, "MIGRATIONS", "O_GEOGRAPHY_CODE", ["HOUSEHOLDS", "JOBS"], "DISTANCE")
      self.assertTrue(rmse(production(xd=[Test.dataset.HOUSEHOLDS.values, Test.dataset.JOBS.values]), production.impl.yhat) < 1e-10)
      Test.dataset["HH_CHANGED"] = Test.dataset.HOUSEHOLDS
      Test.dataset.loc[Test.dataset.D_GEOGRAPHY_CODE == "E07000178", "HH_CHANGED"] = Test.dataset.loc[Test.dataset.D_GEOGRAPHY_CODE == "E07000178", "HOUSEHOLDS"] + 300000 
      Test.dataset["J_CHANGED"] = Test.dataset.JOBS
      Test.dataset.loc[Test.dataset.D_GEOGRAPHY_CODE == "E07000178", "J_CHANGED"] = Test.dataset.loc[Test.dataset.D_GEOGRAPHY_CODE == "E07000178", "JOBS"] + 300000 
      self.assertTrue(rmse(production(xd=[Test.dataset.HH_CHANGED.values, Test.dataset.HH_CHANGED.values]), production.impl.yhat) > 1.0)

  def test_attraction(self):
    # single factor prod
    for model_subtype in ["pow", "exp"]:
      attraction = models.Model("attraction", model_subtype, Test.dataset, "MIGRATIONS", "PEOPLE", "D_GEOGRAPHY_CODE", "DISTANCE")
      self.assertTrue(rmse(attraction(xo=Test.dataset.PEOPLE.values), attraction.impl.yhat) < 1e-10)
      Test.dataset["P_CHANGED"] = Test.dataset.PEOPLE
      Test.dataset.loc[Test.dataset.D_GEOGRAPHY_CODE == "E07000178", "P_CHANGED"] = Test.dataset.loc[Test.dataset.D_GEOGRAPHY_CODE == "E07000178", "HOUSEHOLDS"] + 300000 
      self.assertTrue(rmse(attraction(xo=Test.dataset.P_CHANGED.values), attraction.impl.yhat) > 1.0)

if __name__ == "__main__":
  unittest.main()