#!/usr/bin/env python3

""" 
Creates a GB-wide lookup table of OA-LSOA-MSOA-LAD-CMLAD from scattered datasets
For Scotland LSOA = DataZone, MSOA=Intermediate zone, LAD=Council Area
CMLAD refers to census-merged LAD codes for E&W
"""
import numpy as np
import pandas as pd


def update_lad_codes(df):
  """ 
  Updates for 2013 boundary changes
  nomis etc use the updated codes
  """
  mapping = {
    "E06000048": "E06000057", # Northumberland 
    "E07000097": "E07000242", # E.Herts 
    "E07000100": "E07000240", # St.Albans 
    "E07000101": "E07000243", # Stevenage 
    "E07000104": "E07000241", # Wel.Hat 
    "E08000020": "E08000037", # Gateshead
  } 
  df.replace(mapping, inplace=True)
  # LAD_lookup contains newer codes
  # geog_lookup contains older codes
  # nomis is newer
  # ONS SNPP...?


# TODO convert OD to non-CM LAD (more up to date migration data uses LAD)
lookup = pd.read_csv("../../UrbCap/data/cache/LAD_lookup.csv")
lookup.rename({"GEOGRAPHY_NAME": "LAD_NAME", "GEOGRAPHY": "LAD_NOMIS", "GEOGRAPHY_CODE": "LAD", "CM_GEOGRAPHY": "LAD_CM_NOMIS", "CM_GEOGRAPHY_CODE": "LAD_CM", "URBAN": "LAD_URBAN"}, axis=1, inplace=True)
print(lookup.head())

cmladcodes = lookup["LAD"].unique()

# print(cmladcodes)
# print(len(cmladcodes))

sc_geog_lookup = pd.read_csv("../microsimulation/cache/sc_lookup.csv") \
                  .rename({"OutputArea": "OA","DataZone": "LSOA","InterZone": "MSOA", "Council": "LAD"}, axis=1)
geog_lookup = pd.read_csv("../../Mistral/persistent_data/oa2011codes.csv.gz", compression="infer") \
                  .rename({"oa": "OA","lsoa": "LSOA","msoa": "MSOA", "la": "LAD"}, axis=1) \
                  .append(sc_geog_lookup)
update_lad_codes(geog_lookup)

oacodes = geog_lookup.LAD.unique()

# print(oacodes)
# print(len(oacodes))

problematic = np.intersect1d(cmladcodes, oacodes)

print("XOR:", np.setxor1d(cmladcodes, oacodes))

geog_lookup = geog_lookup.merge(lookup, how="left")

# use LAD code for CM LAD code in Scotland
geog_lookup.loc[geog_lookup.LAD.str.startswith("S"), "LAD_CM"] = geog_lookup[geog_lookup.LAD.str.startswith("S")].LAD

# From https://www.nrscotland.gov.uk/files//geography/2011-census-indexes-csv.zip
sc_lad_names = pd.read_csv("../../Mistral/persistent_data/COUNCIL AREA 2011 LOOKUP.csv").rename({"CouncilArea2011Code": "LAD"}, axis=1) 
geog_lookup = geog_lookup.merge(sc_lad_names[["LAD", "CouncilArea2011Name"]], how="left")
geog_lookup.loc[geog_lookup.LAD_NAME.isnull(), "LAD_NAME"] = geog_lookup[geog_lookup.LAD_NAME.isnull()].CouncilArea2011Name 
geog_lookup.drop("CouncilArea2011Name", axis=1, inplace=True)

# ensure nomis codes are integer not floats
geog_lookup.LAD_NOMIS = geog_lookup.LAD_NOMIS.fillna(-1).astype(int)
geog_lookup.LAD_CM_NOMIS = geog_lookup.LAD_NOMIS.fillna(-1).astype(int)

print(len(geog_lookup))
print(len(geog_lookup.LAD.unique()))
print(geog_lookup.head())
print(geog_lookup[geog_lookup.LAD.str.startswith("S")].head())

filename="../microsimulation/persistent_data/gb_geog_lookup.csv.gz"
geog_lookup.to_csv(filename, index=False, compression="gzip")
print("written to " + filename)


