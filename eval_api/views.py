
from django.http import HttpResponseBadRequest
from annoying.decorators import ajax_request

from evaldontevil import execute_python


def explain_error(exc, code):
    msg = exc.get('exception_type', '') + ': ' + exc.get('exception_msg', '')
    exc['exception_translation'] = msg  # fixme


# Create your views here.
@ajax_request
def eval(request):
    # AJAX request
    # method: POST
    # params: user_script, input_data
    post = request.POST
    if 'user_script' in post and 'input_data' in post:
        user_script = post['user_script']
        input_data = post['input_data']
        explain = False if post.get('explain', True) == 'false' else True

        res = execute_python(user_script, stdin=input_data, explain=explain).__dict__

        if explain:
            del res['stdout'] # exact the same information is present on the last frame - why should it be duplicated?
            del res['stderr'] # see ^

        if 'trace' in res:
            event = res['trace'][-1]
            if event['event'] == 'exception' or event['event'] == 'uncaught_exception':
                explain_error(event, user_script)

        if 'exception' in res and res['exception'] is not None:
            explain_error(res['exception'], user_script)

        return res
    else:
        return HttpResponseBadRequest()
