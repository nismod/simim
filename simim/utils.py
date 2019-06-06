""" helpers for sim prototypes """
import os
import argparse
import numpy as np
import pandas as pd
import hashlib
import json
from scipy.stats.stats import pearsonr 
from scipy.spatial.distance import squareform, pdist

def md5hash(string):
  m = hashlib.md5()
  m.update(string.encode('utf-8'))
  return m.hexdigest()

def get_named_values(dataset, colnames, prefix=""):
  """ Returns a list of Series from dataset, optionally prefixed when modified original values are needed"""
  if not isinstance(colnames, list):
    return dataset[prefix+colnames]
  else:
    return [dataset[prefix+colname] for colname in colnames]


def get_data(local, remote):
  if os.path.isfile(local):
    data = pd.read_csv(local)
  else:
    data = pd.read_csv(remote)
    data.to_csv(local, index=False)
  return data

def calc_distances(gdf):
  # for now makes assumptions about column names and units
  dists = pd.DataFrame(squareform(pdist(pd.DataFrame({"e": gdf.bng_e, "n": gdf.bng_n}))), columns=gdf.lad16cd.unique(), index=gdf.lad16cd.unique())
  # turn matrix into table
  dists = dists.stack().reset_index().rename({"level_0": "orig", "level_1": "dest", 0: "DISTANCE"}, axis=1)
  # convert to km 
  dists.DISTANCE = dists.DISTANCE / 1000.0
  return dists

def dist_weighted_sum(dataset, colname, halfdist, decay_function):
  # exponential decay with half the attraction at 20km
  # apart from London, which decays more slowly due to transport links and wages 
  dataset["LEN"] = halfdist 
  dataset.loc[dataset.D_GEOGRAPHY_CODE.str.startswith("E09"), "LEN"] = 2 * halfdist

  dataset[colname + "_DISTWEIGHTED"] = dataset[colname] * decay_function(dataset.LEN, dataset.DISTANCE)
  wsum = dataset.groupby("D_GEOGRAPHY_CODE")[colname + "_DISTWEIGHTED"].sum().reset_index()
  dataset = dataset.merge(wsum, on="D_GEOGRAPHY_CODE") \
    .drop(colname + "_DISTWEIGHTED_x", axis=1) \
    .rename({colname + "_DISTWEIGHTED_y": colname + "_DISTWEIGHTED"}, axis=1)
  #dataset.to_csv("wdist.csv", index=False)

  return dataset

def r2(fitted, actual):
  return pearsonr(fitted, actual)[0] ** 2

def rmse(fitted, actual):
  return np.sqrt(np.mean((fitted - actual) ** 2))

def od_matrix(dataset, value_col, o_col, d_col):
  return np.nan_to_num(dataset[[value_col, o_col, d_col]].set_index([o_col, d_col]).unstack().values)

def get_config():
  parser = argparse.ArgumentParser(description="spatial interaction model of internal migration")
  parser.add_argument("-c", "--config", required=True, type=str, metavar="config-file", help="the model configuration file (json). See config/default.json")

  args = parser.parse_args()

  with open(args.config) as config_file:
    params = json.load(config_file)
  return params

# throws if problem with inputs, warns for untested settings
def validate_config(params):
  if params["coverage"] !="GB":
    print('Coverage other than "GB" has not been properly tested, proceed with caution')

  if params["model_type"] == "gravity" and "GEOGRAPHY_CODE" in params["emitters"]:
    raise ValueError("Gravity (unconstrained) model requires numeric values for emission factor(s)")  
  if params["model_type"] != "production" and params.emitters != ["GEOGRAPHY_CODE"]:
    raise ValueError("production (constrained) model must use GEOGRAPHY_CODE for emission factor")