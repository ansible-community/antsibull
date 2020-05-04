from twiggy import levels
from twiggy import logger


log: logger.Logger

def quick_setup(min_levels: levels.LogLevel = ...,
                file: t.Optional[str] = ...,
                msg_buffer: int = ...) -> None: ...
