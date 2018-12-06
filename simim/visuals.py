""" visuals.py """

import matplotlib.pyplot as plt

class Visual:
  def __init__(self, rows, cols):
    self.rows = rows
    self.cols = cols
    self.fig, self.axes = plt.subplots(nrows=rows, ncols=cols, figsize=(cols*5, rows*5), sharex=False, sharey=False)

  def panel(self, index):
    return self.axes[index]

  def show(self):
    plt.tight_layout()
    plt.show()

  def to_png(self, filename):
    self.fig.savefig(filename, transparent=True)

