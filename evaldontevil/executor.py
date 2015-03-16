# evaldontevil
#  (eval, don't evil)
#  part of the Pythontutor project
#  https://github.com/vpavlenko/pythontutor-ru


from json import dumps, loads
from os.path import dirname
from sys import stderr

from codejail.jail_code import configure, jail_code, set_limit

from evaldontevil.config import *


configure('python', VENV_PYTHON + '/bin/python', user=USER)

set_limit('CPU', CPUTIME_LIMIT)
set_limit('REALTIME', REALTIME_LIMIT)
set_limit('MEM', MEM_LIMIT)
set_limit('FSIZE', FSIZE_LIMIT)


class ExecuteResult:
	def __init__(self, jailres):
		self.result = 'ok'
		self.stdout = ''
		self.stderr = ''

		if jailres.status & 128 != 0:
			self.result = 'realtime_limited'
			return

		try:
			if jailres.stderr != b'':
				raise Exception(jailres.stderr.decode('utf-8'))

			execplainator_res = loads(str(jailres.stdout, 'utf-8'))

		except Exception as e:
			self.result = 'internal_error'

			stderr.write('Visualizer backend internal error :(\n')
			stderr.write(e.args[0] + '\n')
			stderr.flush()

			return

		self.stdout = execplainator_res['stdout']
		self.stderr = execplainator_res['stderr']

		if self.stderr != '':
			self.result = 'stderr'

		if 'trace' in execplainator_res:
			self.trace = execplainator_res['trace']
			if self.trace[-1]['event'] == 'instruction_limit_reached':
				self.result = 'instructions_limited'
				return

		self.exception = None

		if 'exception' in execplainator_res:
			self.exception = execplainator_res['exception']
			if self.exception is not None:
				self.result = 'unhandled_exception'


def execute_python(code, stdin='', explain=False):
	code = bytes(code, 'utf-8')
	stdin = bytes(stdin, 'utf-8')

	this_dir = dirname(__file__)

	with open(this_dir + '/script.py', 'rb') as script_file:
		script = script_file.read()
		jail_res = jail_code(
			'python', script,

			files = [this_dir + '/execplainator.py', this_dir + '/execplainator_encoder.py'],
			extra_files = [
				('code.py', code),
				('stdin.txt', stdin),
			],

			stdin = bytes(dumps({ # options
				'trace': explain,
			}), 'utf-8'),
		)

		return ExecuteResult(jail_res)
