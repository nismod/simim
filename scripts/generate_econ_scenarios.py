
import pandas as pd

scenario_names = ["scenario1", "scenario2"]

for scenario_name in scenario_names:
  h_scenario = pd.read_csv("data/scenarios/%s.csv" % scenario_name)
  arclads = h_scenario["GEOGRAPHY_CODE"].unique()

  # TODO this baseline seems (slightly?) inconsistent with the scenarios
  baseline = pd.read_csv("data/ce_gva_employment_baseline.csv")
  baseline = baseline[baseline.lad18cd.isin(arclads)].drop(["lad11nm", "lad11cd", "lad18nm"], axis=1).set_index(["year", "lad18cd"])

  scenario = pd.read_csv("data/arc_gva_employment__scenario2.csv")
  scenario = scenario[scenario.lad18cd.isin(arclads)].drop(["lad11nm", "lad11cd", "lad18nm"], axis=1).set_index(["year", "lad18cd"])

  scenario = scenario.join(baseline, lsuffix="_scen", rsuffix="_base")
  scenario["GVA"] = scenario.gva_scen - scenario.gva_base
  scenario["JOBS"] = scenario.employment_scen - scenario.employment_base
  scenario = scenario.drop(["gva_scen", "gva_base", "employment_scen", "employment_base"], axis=1).reset_index().rename({"lad18cd": "GEOGRAPHY_CODE", "year": "YEAR"}, axis=1)
  #print(scenario.loc[scenario.index.get_level_values("lad18cd") == "E07000008"])
  scenario = scenario.merge(h_scenario, on=["YEAR", "GEOGRAPHY_CODE"])
  print(h_scenario[h_scenario.GEOGRAPHY_CODE == "E07000178"])
  print(scenario[scenario.GEOGRAPHY_CODE == "E07000178"])

  scenario.to_csv("data/scenarios/%se.csv" % scenario_name, index=False)

