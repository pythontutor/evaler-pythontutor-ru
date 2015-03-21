# evaldontevil
#  (eval, don't evil)
#  part of the Pythontutor project
#  https://github.com/vpavlenko/pythontutor-ru


# some units for the readability of this config file

GB = 1024 ** 3 # gigabytes
MB = 1024 ** 2 # megabytes
KB = 1024 ** 1 # kilobytes
B  = 1024 ** 0 #     bytes

HRS = 60 ** 2 # hours
MIN = 60 ** 1 # minutes
SEC = 60 ** 0 # seconds


CPUTIME_LIMIT = 3 * SEC # CPU execution time limit
REALTIME_LIMIT = CPUTIME_LIMIT # real execution time limit

MEM_LIMIT = 16 * MB # process virtual memory limit
FSIZE_LIMIT = 8 * KB # maximum size of the files, which may be created by the code


VENV_PYTHON = '/srv/evaldontevil-python' # path to the python virtual environment, which will be used for code execution
USER = 'pythontutor-sandbox' # user, which will be used for code execution. Set to None if you don't want to set user or you don't have such permissions
