# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Functionality to work with a venv."""

import os
import typing as t
import venv

import sh


def get_clean_environment() -> t.Dict[str, str]:
    env = os.environ.copy()
    try:
        del env['PYTHONPATH']
    except KeyError:
        # We just wanted to make sure there was no PYTHONPATH set...
        # all python libs will come from the venv
        pass
    return env


class VenvRunner:
    """
    Makes running a command in a venv easy.

    Combines venv functionality with sh.

    .. seealso::
        * `sh <https://amoffat.github.io/sh/>`_
        * :python:mod:`venv`
    """

    def __init__(self, name: str, top_dir: str) -> None:
        """
        Create a venv.

        :arg name: Name of the venv.
        :arg top_dir: Directory the venv will be created inside of.
        """
        self.name = name
        self.top_dir = top_dir
        self.venv_dir: str = os.path.join(top_dir, name)
        venv.create(self.venv_dir, clear=True, symlinks=True, with_pip=True)
        self._python = self.get_command('python')

        # Upgrade pip to the latest version.
        # Note that cryptography stopped building manylinux1 wheels (the only ship manylinux2010) so
        # we need pip19+ in order to work now.  RHEL8 and Ubuntu 18.04 contain a pip that's older
        # than that so we must upgrade to something even if it's not latest.
        self._python('-m', 'pip', 'install', '--upgrade', 'pip')

    def get_command(self, executable_name) -> sh.Command:
        """
        Return an :sh:obj:`sh.Command` for the given program installed within the venv.

        :arg executable_name: Program to return a command for.
        :returns: An :obj:`sh.Command` that will invoke the program.
        """
        return sh.Command(os.path.join(self.venv_dir, 'bin', executable_name))

    def install_package(self, package_name: str) -> sh.RunningCommand:
        """
        Install a python package into the venv.

        :arg package_name: This can be a bare package name or a path to a file.  It's passed
            directly to :command:`pip install`.
        :returns: An :sh:obj:`sh.RunningCommand` for the pip output.
        """
        return self._python('-m', 'pip', 'install', package_name, _env=get_clean_environment())


class FakeVenvRunner:
    """
    Simply runs commands.

    .. seealso::
        * `sh <https://amoffat.github.io/sh/>`_
        * :python:mod:`venv`
    """

    def get_command(self, executable_name) -> sh.Command:
        """
        Return an :sh:obj:`sh.Command` for the given program installed within the venv.

        :arg executable_name: Program to return a command for.
        :returns: An :obj:`sh.Command` that will invoke the program.
        """
        return sh.Command(executable_name)

    def install_package(self, package_name: str) -> sh.RunningCommand:
        """
        Install a python package into the venv.

        :arg package_name: This can be a bare package name or a path to a file.  It's passed
            directly to :command:`pip install`.
        :returns: An :sh:obj:`sh.RunningCommand` for the pip output.
        """
        raise Exception('Not implemented')
