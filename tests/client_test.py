# Copyright (c) 2010-2017 Samuel Abels
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from __future__ import unicode_literals, print_function
import sys
import unittest
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from telemetric import TMClient

dirname = os.path.dirname(__file__)


class ClientTest(unittest.TestCase):

    def setUp(self):
        pass

    def testConstructor(self):
        client = TMClient('192.168.0.1', 8777)
        #TODO

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(ClientTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
