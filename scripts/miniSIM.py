#!/usr/bin/env python3

import numpy as np
import pandas as pd

from spint import Gravity, Attraction, Production

def main():

  dataset = pd.read_csv("./tests/data/testdata.csv.gz")

  #subset = ["E09000033","E07000010","E06000003","E06000004","E06000002"]
  #subset = ['S12000033', 'E07000068', 'E07000078', 'E07000181', 'E06000035']
  # np.random.seed(0)
  subset = np.random.choice(dataset.O_GEOGRAPHY_CODE.unique(), size=5, replace=False)
  print(subset)

  # filter the subset, needs to be sorted by D then O for both prod and attr
  dataset = dataset[(dataset.O_GEOGRAPHY_CODE.isin(subset)) & (dataset.D_GEOGRAPHY_CODE.isin(subset))] \
    .sort_values(["D_GEOGRAPHY_CODE", "O_GEOGRAPHY_CODE"])
    #.reset_index()

  # merge into 2xN array...?
  attractors = ["HOUSEHOLDS", "JOBS"]
  prod = Production(dataset.MIGRATIONS.values, dataset.O_GEOGRAPHY_CODE.values, dataset[attractors].values, dataset.DISTANCE.values, "pow")

  print(prod.pseudoR2)
  print(prod.SRMSE)

  # NxN with M attrs
  # k  mu     alpha beta
  # 0  1..N-1   M    N+M

  k = prod.params[0]
  mu = np.append(0, prod.params[1:len(subset)])
  alpha = prod.params[len(subset):len(subset)+len(attractors)]
  beta = prod.params[-1]
  print(prod.params)
  print("k =", k)
  print("mu =", mu)
  print("alpha =", alpha)
  print("beta =", beta)

  dataset["YHAT"] = prod.yhat
  # calc yhat manually, expand out mu
  mu_vector = np.tile(mu, len(subset))
  dataset["YHAT_MANUAL"] = np.exp(k) * np.exp(mu_vector) * dataset.HOUSEHOLDS ** alpha[0] * dataset.JOBS ** alpha[1] * dataset.DISTANCE ** beta
  dataset["ABS"] = dataset.YHAT_MANUAL - dataset.YHAT
  dataset["REL"] = dataset.ABS / dataset.YHAT

  print(dataset[np.abs(dataset.YHAT_MANUAL - dataset.YHAT) > 0.0001])
  #print(dataset)

  #dataset.sort_values(["O_GEOGRAPHY_CODE", "D_GEOGRAPHY_CODE"], inplace=True)


  # attr = Attraction(dataset.MIGRATIONS.values, dataset.D_GEOGRAPHY_CODE.values, dataset.PEOPLE.values, dataset.DISTANCE.values, "pow")
  # k = attr.params[0]
  # mu = attr.params[-2]
  # alpha = np.append(0, attr.params[1:len(subset)])
  # beta = attr.params[-1]
  # print("k =", k)
  # print("mu =", mu)
  # print("alpha =", alpha)
  # print("beta =", beta)

  # dataset["YHAT"] = attr.yhat
  # # calc yhat manually, expand out mu
  # alpha_vector = np.repeat(alpha, len(subset))
  # dataset["YHAT_MANUAL"] = np.exp(k) * dataset.PEOPLE ** mu * np.exp(alpha_vector) * dataset.DISTANCE ** beta
  # dataset["ABS"] = dataset.YHAT_MANUAL - dataset.YHAT
  # dataset["REL"] = dataset.ABS / dataset.YHAT

  # print(dataset[np.abs(dataset.YHAT_MANUAL - dataset.YHAT) > 0.0001])
  # #print(dataset)

if __name__ == "__main__":
  main()
