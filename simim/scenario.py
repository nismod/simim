"""
scenario.py
Manages scenarios
"""

import pandas as pd

class Scenario():
  def __init__(self, filename, factors):
    self.data = pd.read_csv(filename)
    if isinstance(factors, str):
      factors = [factors]
    missing = [factor for factor in factors if factor not in self.data.columns] 

    print("Available factors:", factors)
    print("Scenario factors:", [f for f in self.data.columns.values if not f.startswith("CUM_") and f not in ["GEOGRAPHY_CODE", "YEAR"]])
    print("Scenario timeline:", self.timeline())

    # add columns for factors not in scenario
    # TODO is this actually necessary?
    for col in missing:
      self.data[col] = 0
      self.data["CUM_"+col] = 0

    # validate
    if "GEOGRAPHY_CODE" not in self.data.columns.values:
      raise ValueError("Scenario definition must contain a GEOGRAPHY_CODE column")
    if "YEAR" not in self.data.columns.values:
      raise ValueError("Scenario definition must contain a YEAR column")

    # work out factors #.remove(["GEOGRAPHY_CODE", "YEAR"]) 
    self.factors = [f for f in self.data.columns.values if not f.startswith("CUM_") and f not in ["GEOGRAPHY_CODE", "YEAR"]]

    self.current_scenario = None
    self.current_time = None

  def timeline(self):
    return sorted(self.data.YEAR.unique())

  def update(self, year):
    """ Returns new scenario if there is data for the given year, otherwise returns the current (cumulative) scenario """
    self.current_time = year
    if year in self.data.YEAR.unique():
      print("Updating scenario")
      self.current_scenario = self.data[self.data.YEAR==year]
      return self.current_scenario
    else:
      print("Persisting existing scenario")
      return self.current_scenario


  def apply(self, dataset, year):
    # if no scenario for a year, reuse the most recent (cumulative) figures
    self.current_scenario = self.update(year)

    # TODO we can probably get away with empty scenario?
    # ensure there is a scenario
    if self.current_scenario is None:
      raise ValueError("Unable to find a scenario for %s" % year)
    #print(most_recent_scenario.head())
    dataset = dataset.merge(self.current_scenario.drop(self.factors, axis=1), how="left", left_on="D_GEOGRAPHY_CODE", right_on="GEOGRAPHY_CODE") \
      .drop(["GEOGRAPHY_CODE", "YEAR"], axis=1).fillna(0)
    for factor in self.factors:
      # skip constrained
      if factor != "O_GEOGRAPHY_CODE" and factor != "D_GEOGRAPHY_CODE":
        dataset["CHANGED_" + factor] = dataset[factor] + dataset["CUM_" + factor]

    return dataset

