""" visuals.py """

import matplotlib.pyplot as plt

# https://matplotlib.org/examples/color/colormaps_reference.html

class Visual:
  def __init__(self, rows, cols):
    self.rows = rows
    self.cols = cols
    self.fig, self.axes = plt.subplots(nrows=rows, ncols=cols, figsize=(cols*5, rows*5), sharex=False, sharey=False)

  def panel(self, index):
    return self.axes[index]

  def scatter(self, panel, x, y, marker="k.", title=None, **kwargs):
    ax = self.axes[panel]
    if title:
      ax.set_title(title)
    ax.plot(x, y, marker, **kwargs)

  def matrix(self, panel, matrix, cmap="Greys", title=None, **kwargs):
    ax = self.axes[panel]
    if title:
      ax.set_title(title)
    ax.imshow(matrix, cmap=cmap, **kwargs)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)

  def map(self, panel):
    pass

  def show(self):
    plt.tight_layout()
    plt.show()

  def to_png(self, filename):
    self.fig.savefig(filename, transparent=True)

