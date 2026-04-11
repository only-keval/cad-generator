import cadquery as cq
import math
import traceback
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionError:
    stage: str          # "exec" | "missing_build" | "build"
    error_type: str
    message: str
    traceback: str
    file: Optional[str]
    line: Optional[int]
    function: Optional[str]


def _extract_error(e: Exception, stage: str) -> ExecutionError:
    tb = e.__traceback__
    last_tb = tb
    while last_tb and last_tb.tb_next:
        last_tb = last_tb.tb_next

    if last_tb is None:
        file = line = function = None
    else:
        frame = last_tb.tb_frame
        file = frame.f_code.co_filename
        line = last_tb.tb_lineno
        function = frame.f_code.co_name

    return ExecutionError(
        stage=stage,
        error_type=type(e).__name__,
        message=str(e),
        traceback="".join(traceback.format_exception(type(e), e, tb)),
        file=file,
        line=line,
        function=function,
    )


_SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "ascii": ascii,
    "bin": bin, "bool": bool, "bytearray": bytearray, "bytes": bytes,
    "callable": callable, "chr": chr, "classmethod": classmethod,
    "complex": complex, "dict": dict, "divmod": divmod,
    "enumerate": enumerate, "float": float, "format": format,
    "frozenset": frozenset, "hash": hash, "hex": hex, "int": int,
    "isinstance": isinstance, "issubclass": issubclass, "iter": iter,
    "len": len, "list": list, "map": map, "max": max, "min": min,
    "next": next, "oct": oct, "ord": ord, "pow": pow, "range": range,
    "repr": repr, "reversed": reversed, "round": round, "set": set,
    "slice": slice, "sorted": sorted, "staticmethod": staticmethod,
    "str": str, "sum": sum, "tuple": tuple, "zip": zip,
}


class CadqueryExecutor:
    def run(self, script: str) -> tuple[Optional[cq.Shape | cq.Workplane], Optional[ExecutionError]]:
        safe_globals = {
            "__builtins__": _SAFE_BUILTINS,
            "math": math,
            "cq": cq,
        }
        local_env = {}

        try:
            exec(script, safe_globals, local_env)
        except Exception as e:
            return None, _extract_error(e, "exec")

        if "build" not in local_env:
            return None, ExecutionError(
                stage="missing_build",
                error_type="MissingBuildFunction",
                message="build() was not defined.",
                traceback="", file=None, line=None, function=None,
            )

        try:
            result = local_env["build"]()
        except Exception as e:
            return None, _extract_error(e, "build")

        return result, None
