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


class Model:
  def __init__(self, model_type, model_subtype, dataset, y_col, xo_cols, xd_cols, cost_col):
    self.model_type = model_type
    self.model_subtype = model_subtype
    validate(self.model_type, self.model_subtype)

    # take a copy of the input dataset
    self.dataset = dataset.copy()

    self.y_col = y_col
    self.xo_cols = xo_cols
    self.xd_cols = xd_cols
    self.cost_col = cost_col

    if self.model_type == "gravity":
      self.impl = Gravity(self.dataset[self.y_col].values, 
                          self.dataset[self.xo_cols].values, 
                          self.dataset[self.xd_cols].values, 
                          self.dataset[self.cost_col].values, self.model_subtype)
    elif self.model_type == "production":
      self.impl = Production(self.dataset[self.y_col].values, 
                             self.dataset[self.xo_cols].values, 
                             self.dataset[self.xd_cols].values, 
                             self.dataset[self.cost_col].values, self.model_subtype)
    elif self.model_type == "attraction":
      self.impl = Attraction(self.dataset[self.y_col].values, 
                             self.dataset[self.xd_cols].values, 
                             self.dataset[self.xo_cols].values, 
                             self.dataset[self.cost_col].values, self.model_subtype)
    else: #model_type == "doubly":
      self.impl = Doubly(self.dataset[self.y_col].values, 
                         self.dataset[self.xo_cols].values, 
                         self.dataset[self.xd_cols].values, 
                         self.dataset[self.cost_col].values, self.model_subtype)

    # append the model-fitted flows to the dataframe, prefixed with "MODEL_"
    self.dataset["MODEL_"+self.y_col] = self.impl.yhat

  # TODO generalise...
  def k(self):
    return self.impl.params[0]

  def mu(self):
    return self.impl.params[1]

  def alpha(self):
    return self.impl.params[2]

  def beta(self):
    return self.impl.params[3]

  def __call__(self, xo, xd):
    if self.model_type == "gravity":
      if self.model_subtype == "pow":
        ybar = (np.exp(self.k()) * xo ** self.mu() * xd ** self.alpha() * self.dataset[self.cost_col] ** self.beta())
      else:
        ybar = (np.exp(self.k()) * xo ** self.mu() * xd ** self.alpha() * np.exp(self.dataset[self.cost_col] * self.beta()))
      return ybar
    else:
      raise NotImplementedError("TODO...")




