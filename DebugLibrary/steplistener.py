import inspect
import os

from .globals import context


class RobotLibraryStepListenerMixin:
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self):
        super(RobotLibraryStepListenerMixin, self).__init__()
        self.ROBOT_LIBRARY_LISTENER = [self]

    def _start_keyword(self, name, attrs):
        context.current_source_path = ''
        context.current_source_lineno = 0

        if not is_step_mode():
            return

        find_runner_step()
        step = context.current_runner_step

        path = ''
        if hasattr(step, 'lineno'):
            path = step.source
            lineno = step.lineno
        elif 'lineno' in attrs:
            path = attrs['source']
            lineno = attrs['lineno']

        if path and os.path.isdir(path):
            # we might be in folder-wide __init__.robot, but listener args are not telling us that
            # - gives us only the folder path.
            init_path = os.path.join(path, '__init__.robot')
            if os.path.exists(init_path):
                path = init_path

        if path:
            lineno_0_based = lineno - 1
            context.current_source_path = path
            context.current_source_lineno = lineno
            print('> {}({})'.format(path, lineno))
            line = (open(path).readlines()[lineno_0_based].strip())
            print('-> {}'.format(line))

        if attrs['assign']:
            assign = '%s = ' % ', '.join(attrs['assign'])
        else:
            assign = ''
            name = '{}.{}'.format(attrs['libname'], attrs['kwname'])

        translated = '{}{}  {}'.format(assign, name, '  '.join(attrs['args']))
        print('=> {}'.format(translated))

        # callback debug interface
        self.debug()

    start_keyword = _start_keyword


# Hack to find the current runner Step to get the source path and line number.
# This method relies on the internal implementation logic of RF and may need
# to be modified when there are major changes to RF.
def find_runner_step():
    stack = inspect.stack()
    for frame in stack:
        if (frame.function == 'run_steps'  # RobotFramework < 4.0
                or frame.function == 'run'):  # RobotFramework >= 4.0
            arginfo = inspect.getargvalues(frame.frame)
            context.current_runner = arginfo.locals.get('runner')
            context.current_runner_step = arginfo.locals.get('step')
            if context.current_runner_step:
                break


def set_step_mode(on=True):
    context.in_step_mode = on


def is_step_mode():
    return context.in_step_mode
