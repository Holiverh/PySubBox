
# Copyright (C) 2011 by Oliver Ainsworth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import time
import re

def minutes(count=1): return count * 60
def hours(count=1): return count * 60 * minutes()
def days(count=1): return count * 24 * hours()
def weeks(count=1): return count * 7 * days()
def months(count=1): return count * 4 * weeks()

class ExclusionRule(object):
		
	def __init__(self, expression):

		self.expression = str(expression)
		self.vars = {
					# Builtins we want to keep
					"True": True,
					"False": True,
					"abs": abs,
					"sum": sum,
					"re": re,
					# Other stuff
					"all": True,
					"force": False,
					"now": time.time,
					"minutes": minutes,
					"hours": hours,
					"days": days,
					"weeks": weeks,
					"months": months,
					}
		
	def evaluate(self, entry):
		
		context_dict = dict({"__builtins__": None, "entry": entry}, **self.vars)
		return bool(eval(self.expression, context_dict, {}))
