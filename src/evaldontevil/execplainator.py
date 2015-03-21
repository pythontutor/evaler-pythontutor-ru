# evaldontevil
#  (eval, don't evil)
#  part of the Pythontutor project
#  https://github.com/vpavlenko/pythontutor-ru


# This is a modified copy of pg_logger.py from the
#   Online Python Tutor (https://github.com/pgbovine/OnlinePythonTutor/)
# It is Python 3 ready, and less restrictive.

# -----------------------------------------------------------------------------

# Online Python Tutor
# https://github.com/pgbovine/OnlinePythonTutor/
# 
# Copyright (C) 2010-2012 Philip J. Guo (philip@pgbovine.net)
# 
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# -----------------------------------------------------------------------------

# This is a execplainator module. It will execute the user code, and then
# give back to the evaldontevil a detailed step-by-step examplanation, how
# code really did work.

# P.S. This code is supposed to be executed in the secure environment (those
# will do by dontevil), so there is not so much security checks and restrictions.


from bdb import Bdb
from copy import copy
from io import StringIO
from traceback import print_exc
import sys

from execplainator_encoder import encode


# upper-bound on the number of executed lines, in order to guard against
# infinite loops
MAX_EXECUTED_LINES = 1000


def type_name(obj):
    t = type(obj)

    module = t.__module__
    if module == 'builtins':
        if hasattr(t, '__qualname__'):
            return t.__qualname__
        else: # http://bugs.python.org/issue13577
            return t.__name__ # __qualname__ is not present on builtin methods and functions on Python <= 3.2

    return t.__module__ + '.' + t.__qualname__

def parse_exception(exc):
    exception = {}

    if isinstance(exc[1], SyntaxError):
        exception['line'] = exc[1].args[1][1]
        exception['offset'] = exc[1].args[1][2]
    else:
        traceback = exc[2]
        while traceback is not None: # let's walk up to the user code frame
            if traceback.tb_frame.f_code.co_filename == '<string>':
                break

            traceback = traceback.tb_next

        assert traceback is not None

        if hasattr(traceback, 'tb_lineno'):
            exception['line'] = traceback.tb_lineno

        if hasattr(traceback, 'tb_offset'):
            exception['offset'] = traceback.tb_offset

    exception['exception_type'] = type_name(exc[1])

    if hasattr(exc[1], 'msg'):
        exception['exception_msg'] = exc[1].msg
    elif hasattr(exc[1], 'args') and len(exc[1].args) > 0:
        exception['exception_msg'] = exc[1].args[0]

    exception['exception_str'] = exception['exception_type'] + ': ' + exception['exception_msg']

    return exception


class StopExecution(Exception):
    pass


class TraceEntry:
    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)

    def __setattr__(self, name, value):
        if type(value) is dict:
            value = copy(value)
            for k, v in value.items():
                value[k] = encode(v)

        super.__setattr__(self, name, value)

    def dict(self):
        return self.__dict__


class Execplainator(Bdb):
    def __init__(self):
        Bdb.__init__(self)

        self.mainpyfile = ''
        self.filter_var_dict_wait_for_mainpyfile = 0

        # each entry contains a dict with the information for a single
        # executed line
        self.trace = []

        self._exception = None


    def reset(self):
        Bdb.reset(self)
        self.forget()

    def forget(self):
        self.lineno = None
        self.stack = []
        self.curindex = 0
        self.curframe = None

    def setup(self, f, t):
        self.forget()
        self.stack, self.curindex = self.get_stack(f, t)
        self.curframe = self.stack[self.curindex][0]


    def _filter_variables(self, d, dontfilter=()):
        ret = {}

        for k, v in d.items():
            if (not (k.startswith('__') and k.endswith('__')) and k not in __builtins__) or k in dontfilter:
                ret[k] = v

        return ret


    # Override Bdb methods

    def user_call(self, frame, argument_list):
        """This method is called when there is the remote possibility
        that we ever need to stop in this function."""

        if self._wait_for_mainpyfile:
            return

        if self.stop_here(frame):
            self.interaction(frame, None, 'call')

    def user_line(self, frame):
        """This function is called when we stop or break at this line."""

        if self._wait_for_mainpyfile:
            if (self.canonic(frame.f_code.co_filename) != '<string>' or frame.f_lineno <= 0):
                return
            self._wait_for_mainpyfile = 0

        self.interaction(frame, None, 'step_line')

    def user_return(self, frame, return_value):
        """This function is called when a return trap is set here."""

        frame.f_locals['__return__'] = return_value
        self.interaction(frame, None, 'return')

    def user_exception(self, frame, exc_info):
        """This function is called if an exception occurs,
        but only if we are to stop at or just below this level."""

        exc_type, exc_value, exc_traceback = exc_info

        frame.f_locals['__exception__'] = exc_type, exc_value
        exc_type_name = exc_type if type(exc_type) == str else exc_type.__name__

        self.interaction(frame, exc_traceback, 'exception')


    # General interaction function
    def interaction(self, frame, traceback, event_type):
        self.setup(frame, traceback)
        tos = self.stack[self.curindex]
        func_name = tos[0].f_code.co_name
        lineno = tos[1]

        where = frame.f_code.co_filename
        if where != '<string>': # this is not a user code frame
            return # so just skip it

        if func_name in ('<listcomp>', '<genexpr>') and event_type != 'step_line':
            return # skip step line in generator and list comprehensions - they're useless

        # each element is a pair of (function name, locals dict)
        stack_locals = []

        # climb up until you find '<module>', which is (hopefully) the global scope
        i = self.curindex
        while True:
            cur_frame = self.stack[i][0]
            where = cur_frame.f_code.co_name
            if where == '<module>':
                break

            # special case for lambdas - grab their line numbers too
            if where == '<lambda>':
                where = 'lambda on line ' + str(cur_frame.f_code.co_firstlineno)
            elif where == '':
                where = 'unnamed function'

            this_locals = self._filter_variables(cur_frame.f_locals, ('__return__'))

            # filter some internal variables
            # (they're useless and JSON-danger)
            # in the list comprehensions and generators
            if where in ('<listcomp>', '<genexpr>'):
                varnames = list(this_locals.keys())
                for name in varnames:
                    if name.startswith('.'):
                        del this_locals[name]

            for name, value in this_locals.items():
                this_locals[name] = encode(value)

            stack_locals.append((where, this_locals))

            i -= 1

        trace_entry = TraceEntry(
            event = event_type,

            line = lineno,
            func_name = func_name,

            globals = self._filter_variables(tos[0].f_globals),
            stack_locals = stack_locals,

            stdout = self.stdout.getvalue(),
            stderr = self.stderr.getvalue(),
        )

        # if there's an exception, then record its info:
        if event_type == 'exception':
            # always check in f_locals
            exc_type, exc_value = frame.f_locals['__exception__']
            self._exception = parse_exception((exc_type, exc_value, traceback))
            trace_entry.__dict__.update(self._exception)

        self.trace.append(trace_entry)

        if len(self.trace) >= MAX_EXECUTED_LINES:
            self.trace.append(TraceEntry(event='instruction_limit_reached', exception_msg='Stopped after ' + str(MAX_EXECUTED_LINES) + ' steps to prevent possible infinite loop'))
            self.force_terminate()

        self.forget()


    def run_code(self, code, input_data):
        # When bdb sets tracing, a number of call and line events happens
        # BEFORE debugger even reaches user's code (and the exact sequence of
        # events depends on python version). So we take special measures to
        # avoid stopping before we reach the main script (see user_line and
        # user_call for details).
        self._wait_for_mainpyfile = 1


        self.sys_stdin = sys.stdin
        self.stdin = StringIO(input_data)
        sys.stdin = self.stdin

        self.sys_stdout = sys.stdout
        self.stdout = StringIO()
        sys.stdout = self.stdout

        self.sys_stderr = sys.stderr
        self.stderr = StringIO()
        sys.stderr = self.stderr


        user_globals = {
            '__name__': '__main__',
            '__builtins__': __builtins__,
            '__stdin__': self.stdin,
            '__stdout__': self.stdout,
            '__stderr__': self.stderr,
        }

        try:
            self.run(code, user_globals, user_globals)

        except StopExecution:
            pass

        except:
            print_exc()
            exception = parse_exception(sys.exc_info())

            trace_entry = TraceEntry(event='uncaught_exception', **exception)
            self.trace.append(trace_entry)

        sys.stdin = self.sys_stdin
        sys.stdout = self.sys_stdout
        sys.stderr = self.sys_stderr

        return {
            'trace': self._filter_trace(self.trace),
            'exception': self._exception,
            'stdout': self.stdout.getvalue(),
            'stderr': self.stderr.getvalue(),
        }


    def force_terminate(self):
        raise StopExecution()


    def _filter_trace(self, trace):
        # filter all entries after 'return' from '<module>', since they
        # seem extraneous:
        res = []
        for e in trace:
            res.append(e.dict())
            if e.event == 'return' and e.func_name == '<module>':
                break

        # another hack: if the SECOND to last entry is an 'exception'
        # and the last entry is return from <module>, then axe the last
        # entry, for aesthetic reasons :)
        if len(res) >= 2 and \
           res[-2]['event'] == 'exception' and \
           res[-1]['event'] == 'return' and res[-1]['func_name'] == '<module>':
            res.pop()

        return res


class SimpleExecplainator(Bdb):
    def run_code(self, code, input_data):
        exception = None # pah-pah-pah :)

        self.sys_stdin = sys.stdin
        self.stdin = StringIO(input_data)
        sys.stdin = self.stdin

        self.sys_stdout = sys.stdout
        self.stdout = StringIO()
        sys.stdout = self.stdout

        self.sys_stderr = sys.stderr
        self.stderr = StringIO()
        sys.stderr = self.stderr


        user_globals = {
            '__name__': '__main__',
            '__builtins__': __builtins__,
            '__stdin__': self.stdin,
            '__stdout__': self.stdout,
            '__stderr__': self.stderr,
        }

        try:
            self.run(code, user_globals, user_globals)

        except StopExecution:
            pass

        except:
            print_exc()
            try:
                exception = parse_exception(sys.exc_info())
            except AssertionError:
                sys.stderr = self.sys_stderr
                print_exc()


        sys.stdin = self.sys_stdin
        sys.stdout = self.sys_stdout
        sys.stderr = self.sys_stderr

        return {
            'exception': exception,
            'stdout': self.stdout.getvalue(),
            'stderr': self.stderr.getvalue(),
        }


# exec code with full explanation (trace)
def exec(code, input_data=''):
    execplainator = Execplainator()
    return execplainator.run_code(code, str(input_data))

# just execute the code, without explanation, but watch for unhandled exceptions
def simple_exec(code, input_data=''):
    execplainator = SimpleExecplainator()
    return execplainator.run_code(code, str(input_data))
