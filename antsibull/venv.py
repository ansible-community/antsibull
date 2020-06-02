# coding: utf-8
# Author: Toshio Kuratomi <tkuratom@redhat.com>
# License: GPLv3+
# Copyright: Ansible Project, 2020
"""Functionality to work with a venv."""

import os
import venv

import sh


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

    def get_command(self, executable_name) -> sh.Command:
        """
        Return an :sh:obj:`sh.Command` for the given program installed within the venv.

        :arg executable_name: Program to return a command for.
        :returns: An :obj:`sh.Command` that will invoke the program.
        """
        return sh.Command(os.path.join(self.venv_dir, 'bin', executable_name))

    def install_package(self, package_name: str, from_project_path=False) -> sh.RunningCommand:
        """
        Install a python package into the venv.

        :arg package_name: This can be a bare package name or a path to a file.  It's passed
            directly to :command:`pip install`.
        :arg from_project_path: Instead of a package name or file, package_name is a path to a
            project.  ie: an expanded sdist or a checkout of a source repo.  At the moment,
            pip -e is used to install these sorts of packages but this is an implementation
            detail.
        :returns: An :sh:obj:`sh.RunningCommand` for the pip output.
        """
        if from_project_path:
            package_args = ('-e', package_name)
        else:
            package_args = (package_name,)

        return self._python('-m', 'pip', 'install', *package_args)
