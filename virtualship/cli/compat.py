"""Compatibility tooling."""

import os
from typing import Literal


def detect_shell() -> Literal["bash", "zsh", "cmd", "powershell", "unknown"]:
    shell = os.environ.get("SHELL")
    if shell:
        if "bash" in shell:
            return "bash"
        elif "zsh" in shell:
            return "zsh"
    elif os.environ.get("COMSPEC"):
        return "cmd"
    elif os.environ.get("PSModulePath"):
        return "powershell"
    return "unknown"


if detect_shell() in ["bash", "zsh"]:
    DELETE_COMMAND_FMT = "rm -r {path}"
else:
    DELETE_COMMAND_FMT = None
