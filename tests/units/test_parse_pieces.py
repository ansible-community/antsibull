import pytest

from antsibull import dependency_files as df

PIECES = """
community.general
# This is a comment
community.aws
    # Supported by ansible
    ansible.posix
    ansible.windows
# Third parties
purestorage.flasharray
"""

PARSED_PIECES = ['community.general', 'community.aws', 'ansible.posix', 'ansible.windows', 'purestorage.flasharray']

def test_parse_pieces(tmp_path):
    pieces_filename = tmp_path / 'pieces.in'
    with open(pieces_filename, 'w') as f:
        f.write(PIECES)
    assert df.parse_pieces_file(pieces_filename) == PARSED_PIECES
