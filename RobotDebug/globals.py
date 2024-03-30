import re
from enum import Enum

from robot.version import get_version


class SingletonContext:
    in_step_mode = False
    last_command = ""

    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super().__new__(cls)
        return cls.instance


context = SingletonContext()


class StepMode(str, Enum):
    INTO = "_INTO"
    OVER = "_OVER"
    OUT = "_OUT"
    CONTINUE = "_CONTINUE"
    STOP = "_STOP"


IS_RF_7 = int(get_version().split(".", 1)[0]) >= 7  # noqa: PLR2004
KEYWORD_SEP = re.compile(r"[ \t]{2,}|\t")
