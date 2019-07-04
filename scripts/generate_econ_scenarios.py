
import pandas as pd

scenario_names = ["0-unplanned", "1-new-cities", "2-expansion"]

baseline_gva = pd.read_csv("data/arc/arc_gva__baseline.csv")
baseline_emp = pd.read_csv("data/arc/arc_employment__baseline.csv")
baseline_dwl = pd.read_csv("data/arc/arc_dwellings__baseline.csv")

# TODO merge baseline before filter
baseline = baseline[baseline.lad_uk_2016.isin(arclads)].set_index(["year", "lad_uk_2016"])

arclads = pd.read_csv("data/scenarios/camkox_lads.csv").geo_code.unique()

for scenario_name in scenario_names:
  scenario_gva = pd.read_csv("data/arc/arc_gva__{}.csv".format(scenario_name))
  scenario_emp = pd.read_csv("data/arc/arc_employment__{}.csv".format(scenario_name))
  scenario_dwl = pd.read_csv("data/arc/arc_dwellings__{}.csv".format(scenario_name))

  # TODO merge scenario before files
  scenario = scenario[scenario.lad_uk_2016.isin(arclads)].set_index(["year", "lad_uk_2016"])

  scenario = scenario.join(baseline, lsuffix="_scen", rsuffix="_base")
  scenario["GVA"] = scenario.gva_scen - scenario.gva_base
  scenario["JOBS"] = scenario.employment_scen - scenario.employment_base
  scenario["HOUSEHOLDS"] = scenario.dwellings_scen - scenario.dwellings_base
  scenario = scenario[
    ["GVA", "JOBS", "HOUSEHOLDS"]
  ].reset_index().rename({"lad_uk_2016": "GEOGRAPHY_CODE", "year": "YEAR"}, axis=1)

  # output households-only scenario
  scenario[["YEAR", "GEOGRAPHY_CODE", "HOUSEHOLDS"]].to_csv(
    "data/scenarios/scenario{}.csv".format(scenario_name), index=False)

  # output households-gva-jobs scenarios
  scenario.to_csv("data/scenarios/scenario{}e.csv".format(scenario_name), index=False)
