"""
data download functionality
"""

import numpy as np
import pandas as pd

import ukcensusapi.Nomisweb as Nomisweb
import ukcensusapi.NRScotland as NRScotland
import ukcensusapi.NISRA as NISRA

import ukpopulation.myedata as MYEData
import ukpopulation.snppdata as SNPPData
import ukpopulation.nppdata as NPPData
import ukpopulation.utils as ukpoputils


class Instance():
  def __init__(self, params):

    self.coverage = { "EW": ukpoputils.EW, "GB": ukpoputils.GB, "UK": ukpoputils.UK }.get(params["coverage"]) 
    if not self.coverage:
      raise RuntimeError("invalid coverage: %s" % params["coverage"])

    self.cache_dir = params["cache_dir"]
    # initialise data sources
    self.census_ew = Nomisweb.Nomisweb(self.cache_dir)
    self.census_sc = NRScotland.NRScotland(self.cache_dir)
    self.census_ni = NISRA.NISRA(self.cache_dir)
    # projections
    self.mye = MYEData.MYEData(self.cache_dir)
    self.snpp = SNPPData.SNPPData(self.cache_dir) 
    self.npp = NPPData.NPPData(self.cache_dir) 
    # TODO households...

    # scenario data
    self.scenario = pd.read_csv(params["scenario"])

  def scenario_timeline(self):
    # TODO ensure no gaps...fill in?
    return sorted(self.scenario.YEAR.unique().astype(np.int32))

  def get_od(self):

    # get OD data
    # more up-to-date here (E&W by LAD, Scotland & NI by country)
    # https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/migrationwithintheuk/datasets/internalmigrationbyoriginanddestinationlocalauthoritiessexandsingleyearofagedetailedestimatesdataset

    uk_cmlad_codes="1132462081...1132462085,1132462127,1132462128,1132462356...1132462360,1132462086...1132462089,1132462129,1132462130,1132462145...1132462150,1132462229...1132462240,1132462337...1132462351,1132462090...1132462094,1132462269...1132462275,1132462352...1132462355,1132462368...1132462372,1132462095...1132462098,1132462151...1132462158,1132462241...1132462254,1132462262...1132462268,1132462276...1132462282,1132462099...1132462101,1132462131,1132462293...1132462300,1132462319...1132462323,1132462331...1132462336,1132462361...1132462367,1132462111...1132462114,1132462134,1132462135,1132462140...1132462144,1132462178...1132462189,1132462207...1132462216,1132462255...1132462261,1132462301...1132462307,1132462373...1132462404,1132462115...1132462126,1132462136...1132462139,1132462173...1132462177,1132462196...1132462206,1132462217...1132462228,1132462283...1132462287,1132462308...1132462318,1132462324...1132462330,1132462102,1132462103,1132462132,1132462133,1132462104...1132462110,1132462159...1132462172,1132462190...1132462195,1132462288...1132462292,1132462405...1132462484"
    table = "MM01CUK_ALL"
    query_params = {
      "date": "latest",
      "usual_residence": uk_cmlad_codes,
      "address_one_year_ago": uk_cmlad_codes,
      "age": 0,
      "c_sex": 0,
      "measures": 20100,
      "select": "ADDRESS_ONE_YEAR_AGO_CODE,USUAL_RESIDENCE_CODE,OBS_VALUE"
    }
    od = self.census_ew.get_data(table, query_params)
    #print(od_2011.USUAL_RESIDENCE_CODE.unique())
    return od

  def get_people(self, year, geogs):
    # TODO variants...
    if year <= MYEData.MYEData.MAX_YEAR:
      data = self.mye.aggregate(["GENDER", "C_AGE"], geogs, year)
    else:
      data = self.snpp.aggregate(["GENDER", "C_AGE"], geogs, year)

    # TODO: extrapolated SNPP
    #  raise NotImplementedError("TODO auto-extrapolate SNPP...")

    data = data.rename({"OBS_VALUE": "PEOPLE"}, axis=1).drop("PROJECTED_YEAR_NAME", axis=1)

    # print(data.head())
    # print(len(data))
    return data

  def get_households(self):

    # households
    # get total household counts per LAD
    query_params = {
      "date": "latest",
      "RURAL_URBAN": "0",
      "CELL": "0",
      "MEASURES": "20100",
      "geography": "1946157057...1946157404",
      "select": "GEOGRAPHY_CODE,OBS_VALUE"
    }
    households = self.census_ew.get_data("KS105EW", query_params)
    # get Scotland
    households_sc = self.census_sc.get_data("KS105SC", "S92000003", "LAD", category_filters={"KS105SC_0_CODE": 0}).drop("KS105SC_0_CODE", axis=1)
    # print(households_sc)
    # print(len(households_sc))
    households = households.append(households_sc, ignore_index=True)
    #print(len(households))

    if "ni" in self.coverage:
      households_ni = census_ni.get_data("KS105NI", "N92000002", "LAD", category_filters={"KS105NI_0_CODE": 0}).drop("KS105NI_0_CODE", axis=1)
      # print(households_ni)
      # print(len(households_ni))
      households = households.append(households_ni)
      
    households.rename({"OBS_VALUE": "HOUSEHOLDS"}, axis=1, inplace=True)
    return households
