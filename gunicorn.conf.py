import multiprocessing


name = 'evaler-pythontutor-ru'
bind = 'unix:/var/run/evaler-pythontutor-ru/sock.sock'
workers = multiprocessing.cpu_count() * 2 + 1
