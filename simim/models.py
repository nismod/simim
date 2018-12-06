""" models.py """

import numpy as np

from pysal.contrib.spint.gravity import Gravity
from pysal.contrib.spint.gravity import Attraction
from pysal.contrib.spint.gravity import Doubly

_valid_types = ["gravity", "production", "attraction", "doubly"]
_valid_subtypes = ["pow", "exp"]

def validate(model_type, model_subtype):
  if not model_type in _valid_types:
    raise ValueError("invalid model type % (must be one of %s)" % (model_subtype, str(_valid_types)))
  if not model_subtype in _valid_subtypes:
    raise ValueError("invalid model subtype % (must be one of %s)" % (model_subtype, str(_valid_subtypes)))

def solve(model_type, model_subtype, y, xo, xd, c):

  # xo are categorical for prod/doubly constrained models
  # xd are categorical for attr/doubly constrained models

  validate(model_type, model_subtype)

  if model_type == "gravity":
    model = Gravity(y, xo, xd, c, model_subtype)
    # k = gravity.params[0]
    # mu = gravity.params[1]
    # alpha = gravity.params[2]
    # beta = gravity.params[3]

  elif model_type == "production":
    model = Production(y, xo, xd, c, model_subtype)

  elif model_type == "attraction":
    # Attraction constrained model
    model = Attraction(y, xd, xo, c, model_subtype)
    # k = attr.params[0]
    # mu = attr.params[1]

    # alpha = np.append(np.array(0.0), attr.params[2:-1])
    # beta = attr.params[-1]
    # #T_ij = exp(k + mu ln(V_i) + alpha_j + beta * ln?(D_ij))
    # # est_attr = ((np.exp(k) * od_2011.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * od_2011.DISTANCE ** beta).values + 0.5).astype(int)
    # print(len(alpha), len(od_2011.D_GEOGRAPHY_CODE.unique()))

    # T0 = np.exp(k + mu * np.log(od_2011.PEOPLE.values[0]) + alpha[0] + np.log(od_2011.DISTANCE.values[0]) * beta)
    # print(T0, attr.yhat[0])
    # #print(attr.yhat)

  else: #model_type == "doubly":
    model = Doubly(y, xo, xd, c, model_subtype)

  return model

  # TODO perturb
  #  od_2011.loc[od_2011.D_GEOGRAPHY_CODE == "E07000178", "HOUSEHOLDS"] = od_2011.loc[od_2011.D_GEOGRAPHY_CODE == "E07000178", "HOUSEHOLDS"] + 300000 
  #  pert_unc = ((np.exp(k) * od_2011.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * od_2011.DISTANCE ** beta).values + 0.5).astype(int)
  # can only affect rows with the perturbed destination
  # print(np.count_nonzero(pert_unc - est_unc)/len(est_unc)) # =1/378
  # # re-fit model
  # gravity_bumped = Gravity(od_2011.MIGRATIONS.values, od_2011.PEOPLE.values, od_2011.HOUSEHOLDS.values, od_2011.DISTANCE.values, model)
  # print(gravity.params)
  # print(gravity_bumped.params)
  # k = gravity_bumped.params[0]
  # mu = gravity_bumped.params[1]
  # alpha = gravity_bumped.params[2]
  # beta = gravity_bumped.params[3]
  # bump_unc = ((np.exp(k) * od_2011.PEOPLE ** mu * od_2011.HOUSEHOLDS ** alpha * od_2011.DISTANCE ** beta).values + 0.5).astype(int)
  # print("Bumped Unconstrained Poisson Fitted R2 = %f" % gravity_bumped.pseudoR2)
  # print("Bumped Unconstrained Poisson Fitted RMSE = %f" % gravity_bumped.SRMSE)

def recalc(model_type, model_subtype, model, y, xo, xd, c):

  validate(model_type, model_subtype)

  if model_type == "gravity":
    k = model.params[0]
    mu = model.params[1]
    alpha = model.params[2]
    beta = model.params[3]

    if model_subtype == "pow":
      ybar = (np.exp(k) * xo ** mu * xd ** alpha * c ** beta)
    else:
      ybar = (np.exp(k) * xo ** mu * xd ** alpha * np.exp(c * beta))

  else:
    raise NotImplementedError("TODO...")
