# evaldontevil
#  (eval, don't evil)
#  part of the Pythontutor project
#  https://github.com/vpavlenko/pythontutor-ru

# Script, which will be executed in the virtual jailed environment.


from json import dumps, loads
import sys

from execplainator import exec, simple_exec


code = open('code.py', 'r', encoding='utf-8').read()
stdin = open('stdin.txt', 'r', encoding='utf-8').read()

options = loads(sys.stdin.read())

if options['trace']:
	res = exec(code, stdin)
else:
	res = simple_exec(code, stdin)

sys.stdout.write(dumps(res))
