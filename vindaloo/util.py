import subprocess
import os

from io import BytesIO


def cmd(command, print_it=True, get_output=False, extend_environment=None, output_pipe='stdout'):
    return next(do_cmd(command, print_it=print_it, get_output=get_output, extend_environment=extend_environment, output_pipe=output_pipe, stream=False))


def iter_cmd(command, print_it=True, get_output=False, extend_environment=None, output_pipe='stdout'):
    yield from do_cmd(command, print_it=print_it, get_output=get_output, extend_environment=extend_environment, output_pipe=output_pipe, stream=True)


def do_cmd(command, print_it=True, get_output=False, extend_environment=None, output_pipe='stdout', stream=False):

    if print_it:
        print("\n#> ", command, "\n")

    stdout = subprocess.PIPE if get_output else None
    stderr = subprocess.PIPE if get_output else None
    if extend_environment:
        env = os.environ.copy()
        env.update(extend_environment)
    else:
        env = None

    p = None
    data = None

    if get_output:
        data = BytesIO()

    try:
        p = subprocess.Popen(command, shell=True, stdout=stdout, stderr=stderr, env=env)

        if get_output:
            if output_pipe == 'stdout':
                output_stream = p.stdout
            elif output_pipe == 'stderr':
                output_stream = p.stderr
            else:
                raise ValueError('Invalid value for output_pipe')

            while True:
                chunk = output_stream.read(1024)
                if not chunk and p.poll() is not None:
                    break

                if stream:
                    yield chunk.decode("utf-8")
                else:
                    data.write(chunk)

        p.wait()

    except KeyboardInterrupt:
        if p:
            p.kill()
        raise

    if p.returncode == 127:  # Command not found.
        raise Exception('Command "%s" not found' % command)
    elif p.returncode != 0:
        raise Exception('Command "%s" failed with code %s' % (command, p.returncode))

    if data:
        data.seek(0)
        return data.getvalue().decode("utf-8")
