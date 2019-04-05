import os
import numpy as np
import pandas as pd
import simim.data_apis as data_apis
import simim.scenario as scenario

""" 
Scenario 1 ("MISTRAL Arc Scenarios", Usher & Hickford by email 3/19):
Number of new dwellings
From 2020, growth is slowed in existing settlements, decreased to 70% of baseline. The other 30% of baseline plus 19,721 household are split evenly across five new settlements.
 
Each new settlement expands by 4,561 household per annum (from 2020), and has 141,389 households in 2050 (for comparison, Milton Keynes in 2016 has 110,600 households).

Location and nature of settlements
The new settlements are located in the following LADS:
-	Aylesbury Vale: Newtown 01 & Newtown 02
-	Central Bedfordshire: Newtown 03
-	South Cambridgeshire: Newtown 04
-	Huntingdonshire: Newtown 05

"""
g_out = [
  "E07000008",
  "E07000177",
  "E07000099",
  "E06000055",
  "E06000032",
  "E07000179",
  "E07000180",
  "E07000181",
  "E07000155",
  "E06000042",
  "E07000178",
  "E06000030",
  "E07000151",
  "E07000154",
  "E07000156",
  "E07000009",
  "E07000242",
  "E07000243"]
g_in = [
  "E07000004",
  "E06000056",
  "E07000012",
  "E07000011"]

params = {
  "coverage": "GB",
  "model_type": "production",
  "model_subtype": "pow",
  "observation": "MIGRATIONS",
  "emitters": "GEOGRAPHY_CODE",
  "attractors": ["HOUSEHOLDS"],
  "cost": "DISTANCE",
  "base_projection": "ppp",
  "scenario_dir": "./data/scenarios",
  "scenario": "scenario2.csv",
  "end_year": 2050,
  "cache_dir": "../microsimulation/cache",
  "output_dir": "./data/output",
  "graphics": False
}

input_data = data_apis.Instance(params)

h = input_data.get_households(2019, g_out)
scen = pd.DataFrame()
for y in range(2020,2051):
  hprev = h.copy()
  h = input_data.get_households(y, g_out)
  delta = h.merge(hprev, on="GEOGRAPHY_CODE")
  delta["D_HOUSEHOLDS"] = -0.3*(delta.HOUSEHOLDS_x - delta.HOUSEHOLDS_y)
  delta = delta.drop(["HOUSEHOLDS_x", "PROJECTED_YEAR_NAME_y", "HOUSEHOLDS_y"], axis=1).rename({"PROJECTED_YEAR_NAME_x": "PROJECTED_YEAR_NAME"}, axis=1)
  redist = -delta["D_HOUSEHOLDS"].sum() / 4
  newtowns = pd.DataFrame({"GEOGRAPHY_CODE": g_in, "PROJECTED_YEAR_NAME": y, "D_HOUSEHOLDS": 4561 + redist})
  newtowns.loc[newtowns.GEOGRAPHY_CODE=="E07000004", "D_HOUSEHOLDS"] += 4651
  delta = delta.append(newtowns, sort=False)
  scen = scen.append(delta, sort=False)

scen.to_csv("data/scenarios/scenario1.csv", index=False)


