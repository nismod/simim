"""
scenario.py
Manages scenarios
"""

import pandas as pd

class Scenario():
  def __init__(self, filename, model_factors):
    self.data = pd.read_csv(filename)
    if isinstance(model_factors, str):
      model_factors = [model_factors]

    self.factors = [f for f in self.data.columns.values if f not in ["GEOGRAPHY_CODE", "YEAR"]]

    missing = [f for f in model_factors if f not in self.data.columns] 

    print("Model factors:", model_factors)
    print("Scenario factors:", self.factors)
    print("Scenario timeline:", self.timeline())
    print("Scenario geographies:", self.geographies())

    # validate
    if "GEOGRAPHY_CODE" not in self.data.columns.values:
      raise ValueError("Scenario definition must contain a GEOGRAPHY_CODE column")
    if "YEAR" not in self.data.columns.values:
      raise ValueError("Scenario definition must contain a YEAR column")

    self.current_scenario = None
    self.current_time = None

  def timeline(self):
    return sorted(self.data.YEAR.unique())

  def geographies(self):
    return sorted(self.data.GEOGRAPHY_CODE.unique())

  def update(self, year):
    """ Returns new scenario if there is data for the given year, otherwise returns the current (cumulative) scenario """
    self.current_time = year
    self.current_scenario = self.data[self.data.YEAR==year]

  def apply(self, dataset, year):
    # if no scenario for a year, reuse the most recent (cumulative) figures
    self.update(year)

    if self.current_scenario is None or len(self.current_scenario) == 0:
      print("No scenario changes for %d" % year)
      return dataset

    print("Updated scenario to %d" % year)

    # apply to origins then destinations
    print(self.current_scenario)
    dataset = dataset.merge(self.current_scenario, how="left", left_on="O_GEOGRAPHY_CODE", right_on="GEOGRAPHY_CODE") \
      .drop(["GEOGRAPHY_CODE", "YEAR"], axis=1).fillna(0)
    print(dataset.columns.values)
    for factor in self.factors:
      dataset["O_" + factor] += dataset[factor]
    dataset.drop(self.factors, axis=1, inplace=True)

    dataset = dataset.merge(self.current_scenario, how="left", left_on="D_GEOGRAPHY_CODE", right_on="GEOGRAPHY_CODE") \
      .drop(["GEOGRAPHY_CODE", "YEAR"], axis=1).fillna(0)
    for factor in self.factors:
      dataset["D_" + factor] += dataset[factor]
    dataset.drop(self.factors, axis=1, inplace=True)

    return dataset

