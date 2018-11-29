""" Test harness """

# Disable "Line too long"
# pylint: disable=C0301

import os
from unittest import TestCase

# test methods only run if prefixed with "test"
class Test(TestCase):
  """ Test harness """

  def test_null(self):
    self.assertTrue(True)

if __name__ == "__main__":
  unittest.main()