"""
scenario.py
Manages scenarios
"""

import pandas as pd

class Scenario():
  def __init__(self, filename, model_factors, od_filename=None):
    # zonal data (essential)
    self.data = pd.read_csv(filename)

    # od data (optional) used for transport accessibility
    #
    # does not need to be the full n*n entries (380*380 for GB LADs), but the submatrix needs
    # to be applied correctly to the overall travel cost matrix
    if od_filename is not None:
      self.od_data = pd.read_csv(od_filename)
    else:
      self.od_data = pd.DataFrame({
        "O_GEOGRAPHY_CODE": [], "D_GEOGRAPHY_CODE": [], "YEAR": []
      })

    if isinstance(model_factors, str):
      model_factors = [model_factors]

    self.factors = [
      f for f in self.data.columns.values
      if f not in ["GEOGRAPHY_CODE", "YEAR"]
    ]

    self.od_factors = [
      f for f in self.od_data.columns.values
      if f not in ["O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE", "YEAR"]
    ]

    missing = [
      f for f in model_factors
      if f not in self.data.columns and f not in self.od_data.columns
    ]

    print("Model factors:", model_factors)
    print("Scenario zonal factors:", self.factors)
    print("Scenario OD factors:", self.od_factors)
    print("Scenario zonal timeline:", self.timeline())
    print("Scenario OD timeline:", self.od_timeline())
    print("Scenario zonal geographies:", self.geographies())
    print("Scenario OD geographies:", self.od_geographies())

    # validate
    if "GEOGRAPHY_CODE" not in self.data.columns.values:
      raise ValueError("Scenario definition must contain a GEOGRAPHY_CODE column")
    if "YEAR" not in self.data.columns.values:
      raise ValueError("Scenario definition must contain a YEAR column")

    if "O_GEOGRAPHY_CODE" not in self.od_data.columns.values:
      raise ValueError("OD scenario definition must contain a O_GEOGRAPHY_CODE column")
    if "D_GEOGRAPHY_CODE" not in self.od_data.columns.values:
      raise ValueError("OD scenario definition must contain a D_GEOGRAPHY_CODE column")
    if "YEAR" not in self.od_data.columns.values:
      raise ValueError("OD scenario definition must contain a YEAR column")

    self.current_scenario = None
    self.current_time = None

  def timeline(self):
    return sorted(self.data.YEAR.unique())

  def od_timeline(self):
    return sorted(self.od_data.YEAR.unique())

  def geographies(self):
    return sorted(self.data.GEOGRAPHY_CODE.unique())

  def od_geographies(self):
    return self.od_data[["O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"]].drop_duplicates()

  def update(self, year):
    """Sets new scenario if there is data for the given year, otherwise empty data
    """
    self.current_time = year
    self.current_scenario = self.data[self.data.YEAR==year]
    self.current_od_scenario = self.od_data[self.od_data.YEAR == year]

  def apply(self, dataset, year):
    """Apply scenario updates to the dataset

    If there's no scenario for a year, reuse the most recent figures
    """
    self.update(year)

    # Zonal scenario
    if self.current_scenario is None or len(self.current_scenario) == 0:
      print("No scenario changes for %d" % year)
    else:
      print("Updated scenario to %d" % year)

      # apply to origins ...
      dataset = dataset.merge(
        self.current_scenario, how="left", left_on="O_GEOGRAPHY_CODE", right_on="GEOGRAPHY_CODE"
      ).drop(
        ["GEOGRAPHY_CODE", "YEAR"], axis=1
      ).fillna(0)

      for factor in self.factors:
        dataset["O_" + factor] += dataset[factor]
      dataset.drop(self.factors, axis=1, inplace=True)

      # ... then destinations
      dataset = dataset.merge(
        self.current_scenario, how="left", left_on="D_GEOGRAPHY_CODE", right_on="GEOGRAPHY_CODE"
      ).drop(
        ["GEOGRAPHY_CODE", "YEAR"], axis=1
      ).fillna(0)

      for factor in self.factors:
        dataset["D_" + factor] += dataset[factor]
      dataset.drop(self.factors, axis=1, inplace=True)

    # OD scenario
    if self.current_od_scenario is None or len(self.current_od_scenario) == 0:
      print("No OD scenario changes for %d" % year)
    else:
      print("Updated OD scenario to %d" % year)
      # apply od scenario to the dataset
      dataset.drop(self.od_factors, axis=1, inplace=True)
      dataset = dataset.merge(
        self.current_od_scenario, how="left", on=["O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"]
      ).drop(
        ["YEAR"], axis=1
      ).fillna(0)

    return dataset
