from contextlib import contextmanager
import os


@contextmanager
def chdir(path):
    orig_dir = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(orig_dir)
