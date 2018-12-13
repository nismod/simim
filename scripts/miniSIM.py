#!/usr/bin/env python3

import numpy as np
import pandas as pd

from pysal.contrib.spint.gravity import Gravity
from pysal.contrib.spint.gravity import Production

def main():

  dataset = pd.read_csv("./tests/data/testdata.csv.gz")

  subset = ["E06000005","E07000010","E06000003","E06000004","E06000002"]
  subset = sorted(['S12000033', 'E07000068', 'E07000078', 'E07000181', 'E06000035'])
  # np.random.seed(0)
  # subset = np.random.choice(dataset.O_GEOGRAPHY_CODE.unique(), size=5, replace=False)
  print(subset)
  
  
  # filter the subset
  dataset = dataset[(dataset.O_GEOGRAPHY_CODE.isin(subset)) & (dataset.D_GEOGRAPHY_CODE.isin(subset))]

  model = Production(dataset.MIGRATIONS.values, dataset.O_GEOGRAPHY_CODE.values, dataset.HOUSEHOLDS.values, dataset.DISTANCE.values, "pow")

  k = model.params[0]
  mu = np.append(0, model.params[1:len(subset)])
  alpha = model.params[-2]
  beta = model.params[-1]
  print("k =", k)
  print("mu =", mu)
  print("alpha =", alpha)
  print("beta =", beta)

  dataset["YHAT"] = model.yhat

  # calc yhat manually, expand out mu
  mu_vector = np.tile(mu, len(subset))
  dataset["YHAT_MANUAL"] = np.exp(k) * np.exp(mu_vector) * dataset.HOUSEHOLDS ** alpha * dataset.DISTANCE ** beta

  print(dataset[np.abs(dataset.YHAT_MANUAL - dataset.YHAT) > 0.0001])

  # # pysal impl
  # model_type = "production"
  # model
  # print("model: " + model)
  # gravity = Gravity(dataset.MIGRATIONS.values, dataset.PEOPLE.values, dataset.HOUSEHOLDS.values, dataset.DISTANCE.values, model)
  # #print(gravity.params)
  # # TODO this formula is wrong?
  # k = gravity.params[0]
  # mu = gravity.params[1]
  # alpha = gravity.params[2]
  # beta = gravity.params[3]
  # if model == "pow":
  #   est_unc = (np.exp(k) * od_2011.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * od_2011.DISTANCE ** beta).values
  # else:
  #   est_unc = (np.exp(k) * od_2011.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * np.exp(od_2011.DISTANCE * beta)).values

  # print("Unconstrained Poisson Fitted R2 = %f" % gravity.pseudoR2)
  # print("Unconstrained Poisson Fitted RMSE = %f" % gravity.SRMSE)
  # print(np.mean(est_unc - gravity.yhat))
  # print(np.sqrt(np.mean((est_unc - gravity.yhat)**2)))

  # print(dir(gravity))
  # print(gravity.X)
  # print(gravity.f)
  # print(od_2011.MIGRATIONS)

  # #perturb
  # od_2011.loc[od_2011.D_GEOGRAPHY_CODE == "E07000178", "HOUSEHOLDS"] = od_2011.loc[od_2011.D_GEOGRAPHY_CODE == "E07000178", "HOUSEHOLDS"] + 300000 
  # pert_unc = ((np.exp(k) * od_2011.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * od_2011.DISTANCE ** beta).values + 0.5).astype(int)

  # can only affect rows with the perturbed destination
  #print(np.count_nonzero(pert_unc - est_unc)/len(est_unc)) # =1/378


if __name__ == "__main__":
  main()