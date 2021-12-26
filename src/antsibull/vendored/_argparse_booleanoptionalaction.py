# This is a copy of BooleanOptionalAction from the Python-3.9 code.
# https://github.com/python/cpython/blob/41b223d29cdfeb1f222c12c3abaccc3bc128f5e7/Lib/argparse.py#L856
# It is licensed under the Python Software Foundation License:
# https://github.com/python/cpython/blob/main/LICENSE
#
# A bug that affects our usage of BoolanOptionalAction was discovered (it displays default: SUPPRESS
# in the help message).  I have added a bugix for that here and will open a PR upstream once
# a maintainer answers a question for me:
# https://github.com/python/cpython/pull/17447/files#r666506839

# The intention is that this is used from antsibull.compat.BooleanOptionalAction rather than from
# this file. That way we use the version in the python stdlib if it is available and use this
# code if it is not.

# pylint:disable=missing-module-docstring,redefined-builtin

from argparse import Action, SUPPRESS, OPTIONAL, ZERO_OR_MORE


def _add_default_to_help_string(action):
    """
    Add the default value to the option help message.

    ArgumentDefaultsHelpFormatter and BooleanOptionalAction both want to add
    the default value to the help message when it isn't already present.  This
    code will do that, detecting cornercases to prevent duplicates or cases
    where it wouldn't make sense to the end user.
    """
    help = action.help

    if '%(default)' not in action.help:
        if action.default is not SUPPRESS:
            defaulting_nargs = [OPTIONAL, ZERO_OR_MORE]
            if action.option_strings or action.nargs in defaulting_nargs:
                help += ' (default: %(default)s)'
    return help


class BooleanOptionalAction(Action):
    def __init__(self,
                 option_strings,
                 dest,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):

        _option_strings = []
        for option_string in option_strings:
            _option_strings.append(option_string)

            if option_string.startswith('--'):
                option_string = '--no-' + option_string[2:]
                _option_strings.append(option_string)

        # if help is not None and default is not None:
        #     help += f" (default: {default})"

        super().__init__(
            option_strings=_option_strings,
            dest=dest,
            nargs=0,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar)

        self.help = _add_default_to_help_string(self)

    def __call__(self, parser, namespace, values, option_string=None):
        if option_string in self.option_strings:
            setattr(namespace, self.dest, not option_string.startswith('--no-'))

    def format_usage(self):
        return ' | '.join(self.option_strings)
