""" helpers for sim prototypes """

import os
import argparse
import numpy as np
import pandas as pd
import requests
import hashlib
import zipfile
import json
import re
import geopandas as gpd
from scipy.stats.stats import pearsonr 
from scipy.spatial.distance import squareform, pdist

def md5hash(string):
  m = hashlib.md5()
  m.update(string.encode('utf-8'))
  return m.hexdigest()

def get_data(local, remote):
  if os.path.isfile(local):
    data = pd.read_csv(local)
  else:
    data = pd.read_csv(remote)
    data.to_csv(local, index=False)
  return data

def get_shapefile(zip_url, cache_dir):
  local_zipfile = os.path.join(cache_dir, md5hash(zip_url) + ".zip")
  if not os.path.isfile(local_zipfile):
    response = requests.get(zip_url)
    response.raise_for_status()
    with open(local_zipfile, 'wb') as fd:
      for chunk in response.iter_content(chunk_size=1024):
        fd.write(chunk)
    print("downloaded OK")
  else: 
    print("using cached data: %s" % local_zipfile)
  
  zip = zipfile.ZipFile(local_zipfile)
  #print(zip.namelist())
  # find a shapefile in the zip...
  regex = re.compile(".*\.shp$")
  f = filter(regex.match, zip.namelist())
  shapefile = str(next(f))
  # can't find a way of reading this directly into geopandas
  zip.extractall(path=cache_dir)
  return gpd.read_file(os.path.join(cache_dir, shapefile))

# TODO split into matrix and table versions?
def calc_distances(gdf):
  # for now makes assumptions about column names and units
  dists = pd.DataFrame(squareform(pdist(pd.DataFrame({"e": gdf.bng_e, "n": gdf.bng_n}))), columns=gdf.lad16cd.unique(), index=gdf.lad16cd.unique())
  # turn matrix into table
  dists = dists.stack().reset_index().rename({"level_0": "orig", "level_1": "dest", 0: "DISTANCE"}, axis=1)
  # convert to km 
  dists.DISTANCE = dists.DISTANCE / 1000.0
  return dists

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

