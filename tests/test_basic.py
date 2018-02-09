import unittest
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "library"))

from library import helper

class BasicTestSuite(unittest.TestCase):
    """Basic test cases."""

    def test_load_config_success(self):
        config = helper.get_config('APP', 'debug')
        assert config == 1


if __name__ == '__main__':
    unittest.main()
