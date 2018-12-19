""" models.py """

import numpy as np

from pysal.contrib.spint.gravity import Gravity
from pysal.contrib.spint.gravity import Attraction
from pysal.contrib.spint.gravity import Production
from pysal.contrib.spint.gravity import Doubly

_valid_types = ["gravity", "production", "attraction", "doubly"]
_valid_subtypes = ["pow", "exp"]

def validate(model_type, model_subtype, dataset, y_col, xo_cols, xd_cols, cost_col):
  if not model_type in _valid_types:
    raise ValueError("invalid model type %s (must be one of %s)" % (model_subtype, str(_valid_types)))
  if not model_subtype in _valid_subtypes:
    raise ValueError("invalid model subtype %s (must be one of %s)" % (model_subtype, str(_valid_subtypes)))
  if not "O_GEOGRAPHY_CODE" in dataset.columns.values:
    raise ValueError("dataset must contain an O_GEOGRAPHY_CODE column for origin identifiers")
  if not "D_GEOGRAPHY_CODE" in dataset.columns.values:
    raise ValueError("dataset must contain an D_GEOGRAPHY_CODE column for destination identifiers")
  if not y_col in dataset.columns.values:
    raise ValueError("observation column specified to be %s but it's not in the dataset" % y_col)
  # TODO validate xo/xd cols...
  if not cost_col in dataset.columns.values:
    raise ValueError("cost function column specified to be %s but it's not in the dataset" % cost_col)

class Model:
  def __init__(self, model_type, model_subtype, dataset, y_col, xo_cols, xd_cols, cost_col):
    self.model_type = model_type
    self.model_subtype = model_subtype
    validate(self.model_type, self.model_subtype, dataset, y_col, xo_cols, xd_cols, cost_col)

    # take a copy of the input dataset and ensure sorted by D then O
    # so that the ordering of mu, alpha is determined
    self.dataset = dataset.sort_values(["D_GEOGRAPHY_CODE", "O_GEOGRAPHY_CODE"])#.reset_index()

    self.y_col = y_col
    self.xo_cols = xo_cols
    self.xd_cols = xd_cols
    self.cost_col = cost_col

    # slightly complicated to compute indices for mu and alpha from params
    self.num_emit = 1 if np.isscalar(self.xo_cols) else len(self.xo_cols)
    self.num_attr = 1 if np.isscalar(self.xd_cols) else len(self.xd_cols)
    # for constrained models the above values need to be changed to num of unique O or D less 1
  
    if self.model_type == "gravity":
      self.impl = Gravity(self.dataset[self.y_col].values, 
                          self.dataset[self.xo_cols].values, 
                          self.dataset[self.xd_cols].values, 
                          self.dataset[self.cost_col].values, self.model_subtype)
    elif self.model_type == "production":
      assert(self.num_emit == 1)
      self.num_emit = len(self.dataset[self.xo_cols].unique()) - 1
      self.impl = Production(self.dataset[self.y_col].values, 
                             self.dataset[self.xo_cols].values, 
                             self.dataset[self.xd_cols].values, 
                             self.dataset[self.cost_col].values, self.model_subtype)
    elif self.model_type == "attraction":
      assert(self.num_attr == 1)
      self.num_attr = len(self.dataset[self.xd_cols].unique()) - 1
      self.impl = Attraction(self.dataset[self.y_col].values, 
                             self.dataset[self.xd_cols].values, 
                             self.dataset[self.xo_cols].values, 
                             self.dataset[self.cost_col].values, self.model_subtype)
    else: #model_type == "doubly":
      assert(self.num_emit == 1)
      self.num_emit = len(self.dataset[self.xo_cols].unique()) - 1
      assert(self.num_attr == 1)
      self.num_attr = len(self.dataset[self.xd_cols].unique()) - 1
      raise NotImplementedError("Doubly constrained model is too constrained")
      self.impl = Doubly(self.dataset[self.y_col].values, 
                         self.dataset[self.xo_cols].values, 
                         self.dataset[self.xd_cols].values, 
                         self.dataset[self.cost_col].values, self.model_subtype)

    # append the model-fitted flows to the dataframe, prefixed with "MODEL_"
    self.dataset["MODEL_"+self.y_col] = self.impl.yhat

  # The params array structure, based on N emissiveness factors and M attractiveness factors:
  #
  #   0 1 ... M M+1 ... N N+1 ... N+M+1 N+M+2 
  # G k m ... m  m ...  m  a ...    a     b
  # P k m ... m  m ...  m  a ...    a     b
  # A k a ... a  m ...  m  m ...    m     b
  # D k m ... m  m ...  m  a ...    a     b
  #
  # for production/doubly, N is unique origins - 1
  # for attraction/doubly, M is unique dests - 1

  def k(self):
    return self.impl.params[0]

  def mu(self):
    if self.model_type == "attraction":
      return self.impl.params[1+self.num_attr:1+self.num_attr+self.num_emit]
    else:
      return self.impl.params[1:self.num_emit+1]

  def alpha(self):
    if self.model_type == "attraction":
      return self.impl.params[1:self.num_attr+1]
    else:
      return self.impl.params[1+self.num_emit:1+self.num_emit+self.num_attr]

  def beta(self):
    return self.impl.params[-1]

  def __calc_xo_mu(self, xo):
    if not isinstance(xo, list):
      xo = [xo]
    mu = self.mu()
    assert len(mu) == self.num_emit
    assert len(xo) == self.num_emit 
    xo_mu = xo[0] ** mu[0]
    for i in range(1,self.num_emit):
      xo_mu = xo_mu * xo[i] ** mu[i]
    return xo_mu

  def __calc_xd_alpha(self, xd):
    if not isinstance(xd, list):
      xd = [xd]
    alpha = self.alpha()
    assert len(alpha) == self.num_attr
    assert len(xd) == self.num_attr 
    xd_alpha = xd[0] ** alpha[0]
    for i in range(1,self.num_attr):
      xd_alpha = xd_alpha * xd[i] ** alpha[i]
    return xd_alpha

  def __call__(self, xo=None, xd=None):
    if self.model_type == "gravity":
      assert xo is not None
      assert xd is not None
      xo_mu = self.__calc_xo_mu(xo)
      xd_alpha = self.__calc_xd_alpha(xd)

      if self.model_subtype == "pow":
        ybar = (np.exp(self.k()) * xo_mu * xd_alpha * self.dataset[self.cost_col] ** self.beta())
      else:
        ybar = (np.exp(self.k()) * xo_mu * xd_alpha * np.exp(self.dataset[self.cost_col] * self.beta()))
      return ybar
    elif self.model_type == "production":
      #assert xo is None
      assert xd is not None
      xd_alpha = self.__calc_xd_alpha(xd)
      mu = np.append(0, self.mu())
      mu = np.tile(mu, int(len(self.dataset)/len(mu)))
      assert len(mu) == len(self.dataset)
      # NB ordering is only guaranteed if dataset is sorted by origin then destination code
      if self.model_subtype == "pow":
        ybar = (np.exp(self.k()) * np.exp(mu) * xd_alpha * self.dataset[self.cost_col] ** self.beta())
      else:
        ybar = (np.exp(self.k()) * np.exp(mu) * xd_alpha * np.exp(self.dataset[self.cost_col] * self.beta()))
      return ybar
    elif self.model_type == "attraction":
      assert xo is not None
      #assert xd is None
      xo_mu = self.__calc_xo_mu(xo)
      alpha = np.append(0,self.alpha())
      alpha = np.repeat(alpha, int(len(self.dataset)/len(alpha)))
      assert len(alpha) == len(self.dataset)
      # NB ordering is only guaranteed if dataset is sorted by origin then destination code
      if self.model_subtype == "pow":
        ybar = (np.exp(self.k()) * xo_mu * np.exp(alpha) * self.dataset[self.cost_col] ** self.beta())
      else:
        ybar = (np.exp(self.k()) * xo_mu * np.exp(alpha) * np.exp(self.dataset[self.cost_col] * self.beta()))
      return ybar
    else:
      raise NotImplementedError("%s evaluation not implemented" % self.model_type)

