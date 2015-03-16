import unittest

from evaldontevil import execute_python


class TestExecutePython(unittest.TestCase):
    def test_list_index_out_of_range(self):
        execution = execute_python('[][0]', stdin='', explain=False)
        self.assertEqual(execution.stderr, 'IndexError: list index out of range')


if __name__ == '__main__':
    unittest.main()
