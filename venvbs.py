#!/usr/bin/env python3
"""
A fun little script to create a virtualenv without installing a damn thing.

python venvbs.py <arguments to virtualenv>
"""
import contextlib
import glob
import io
import json
import logging
import os
import os.path
import shutil
import subprocess
import sys
import tarfile


try:
    from urllib2 import urlopen
    from urllib2 import URLError
except ImportError:
    from urllib.request import urlopen
    from urllib.error import URLError

try:
    from tempfile import TemporaryDirectory
except ImportError:
    import tempfile

    class TemporaryDirectory(object):
        def __init__(self, dir):
            self.dir = dir
            self._tmp = None

        def __enter__(self):
            self._tmp = tempfile.mkdtemp(dir=self.dir)
            return self._tmp

        def __exit__(self, *args):
            shutil.rmtree(self._tmp)


logging.basicConfig(level=logging.INFO)


class BootstrapError(Exception):
    def __init__(self, msg, *args):
        self.msg = msg
        self.args = args

    def __str__(self):
        return self.msg % self.args


def task_get_url(package):
    try:
        logging.info("Locating sdist for: %s", package)
        url = 'https://pypi.python.org/pypi/%s/json' % (package,)
        with contextlib.closing(urlopen(url)) as req:
            data = json.loads(req.read().decode('utf8'))
        urls = [x for x in data['urls'] if x['packagetype'] == 'sdist']
        if len(urls) == 0:
            raise BootstrapError('No URL found for: %s', package)
        final = urls[0]['url']
        logging.info("Found URL: %s", final)
        return final
    except URLError:
        raise BootstrapError('Could not get url')


def task_fetch_virtualenv(dir, url):
    stream = io.BytesIO()
    try:
        logging.info("Downloading virtualenv.")
        with contextlib.closing(urlopen(url)) as virtualenv:
            stream.write(virtualenv.read())
        logging.info("Download complete.")
    except URLError as e:
        args = ("Could not download virtualenv: %s", e.reason)
        raise BootstrapError(*args)
    stream.seek(0)
    try:
        logging.info("Extracting to: %s", dir)
        with tarfile.open(fileobj=stream) as tar:
            tar.extractall(dir)
        logging.info("Successfully extracted.")
    except (tarfile.TarError, ValueError, OSError) as e:
        args = ("Could not untar virtualenv: %s", e.args[0])
        raise BootstrapError(*args)


def task_find_in_bin(dir, executable):
    logging.info("Locating %s", executable)
    pth = os.path.join(dir, 'bin', executable)
    if os.path.isfile(pth) and os.access(pth, os.X_OK):
        logging.info("%s found, and is executable: %s", executable, pth)
        return pth
    raise BootstrapError("%s not found, or not executable.", executable)


def task_find_virtualenvpy(dir):
    logging.info("Locating virtualenv.py")
    pattern = os.path.join(dir, 'virtualenv-*')
    matches = glob.glob(pattern)
    for match in matches:
        candidate = os.path.join(match, 'virtualenv.py')
        if os.path.isfile(candidate):
            logging.info("virtualenv.py found: %s", candidate)
            return candidate
    raise BootstrapError("Could not find virtualenv.py")


def task_create_venv(python, virtualenvpy, venv_args):
    logging.info("Creating virtualenv: %s", venv_args[-1])
    args = [python, virtualenvpy] + list(venv_args)
    code = subprocess.call(args)
    if code != 0:
        raise BootstrapError("Could not create virtualenv.")
    logging.info("Virtualenv created.")


def run(python, venv_args):
    tdlocation = os.getcwd()
    with TemporaryDirectory(dir=tdlocation) as td:
        url = task_get_url('virtualenv')
        task_fetch_virtualenv(td, url)
        virtualenvpy = task_find_virtualenvpy(td)
        task_create_venv(python, virtualenvpy, venv_args)


def main(argv=None):
    try:
        run(sys.executable, argv)
        return
    except BootstrapError as e:
        logging.exception(e.msg, *e.args)
        return e.msg % e.args


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
