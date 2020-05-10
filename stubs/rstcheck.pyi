import docutils.utils

from typing import List, Tuple, Union


def check(source: str,
          filename: str = ...,
          report_level: docutils.utils.Reporter = ...,
          ignore: Union[dict, None] = ...,
          debug: bool = ...) -> List[Tuple[int, str]]: ...
