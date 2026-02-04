"""A wrapper around ROBOT functionality.

.. seealso:: https://robot.obolibrary.org
"""

import logging
import os
import subprocess
from pathlib import Path
from shutil import which
from subprocess import check_output
from textwrap import indent, shorten
from typing import Literal

import pystow

__all__ = [
    "ROBOT_VERSION",
    "ROBOTError",
    "call_robot",
    "convert",
    "get_robot_jar_path",
    "is_available",
]

logger = logging.getLogger(__name__)

#: The default ROBOT version to download
ROBOT_VERSION = "1.9.8"
ROBOT_MODULE = pystow.module("robot")


def get_robot_jar_path(*, version: str | None = None) -> Path:
    """Ensure the robot jar is there."""
    if version is None:
        version = ROBOT_VERSION
    url = f"https://github.com/ontodev/robot/releases/download/v{version}/robot.jar"
    return ROBOT_MODULE.ensure(url=url, version=version)


def is_available() -> bool:
    """Check if ROBOT is available."""
    if which("java") is None:
        # suggested in https://stackoverflow.com/questions/11210104/check-if-a-program-exists-from-a-python-script
        logger.error("java is not on the PATH")
        return False

    try:
        check_output(["java", "--help"])  # noqa: S607
    except Exception:
        logger.error(
            "java --help failed - this means the java runtime environment (JRE) "
            "might not be configured properly"
        )
        return False

    robot_jar_path = get_robot_jar_path()
    if not robot_jar_path.is_file():
        logger.error("ROBOT was not successfully downloaded to %s", robot_jar_path)
        # ROBOT was unsuccessfully downloaded
        return False

    try:
        call_robot(["--help"])
    except Exception:
        logger.error("ROBOT was downloaded to %s but could not be run with --help", robot_jar_path)
        return False

    return True


def call_robot(args: list[str]) -> str:
    """Run a robot command and return the output as a string."""
    rr = ["java", "-jar", str(get_robot_jar_path()), *args]
    logger.debug("Running shell command: %s", rr)
    try:
        ret = check_output(  # noqa:S603
            rr,
            cwd=os.path.dirname(__file__),
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        raise ROBOTError(
            command=e.cmd,
            return_code=e.returncode,
            output=e.output.decode() if e.output is not None else None,
            stderr=e.stderr.decode() if e.stderr is not None else None,
        ) from None

    return ret.decode()


def convert(
    input_path: str | Path,
    output_path: str | Path,
    input_flag: Literal["-i", "-I"] | None = None,
    *,
    merge: bool = False,
    fmt: str | None = None,
    check: bool = True,
    reason: bool = False,
    extra_args: list[str] | None = None,
    debug: bool = False,
) -> str:
    """Convert an OBO file to an OWL file with ROBOT.

    :param input_path: Either a local file path or IRI. If a local file path
        is used, pass ``"-i"`` to ``flag``. If an IRI is used, pass ``"-I"``
        to ``flag``.
    :param output_path: The local file path to save the converted ontology to.
        Will infer format from the extension, otherwise, use the ``fmt`` param.
    :param input_flag: The flag to denote if the file is local or remote.
        Tries to infer from input string if none is given
    :param merge: Use ROBOT's merge command to squash all graphs together
    :param fmt: Explicitly set the format
    :param check:
        By default, the OBO writer strictly enforces
        `document structure rules <http://owlcollab.github.io/oboformat/doc/obo-syntax.html#4>`.
        If an ontology violates these, the convert to OBO operation will fail.
        These checks can be ignored by setting this to false.
    :param reason:
        Turn on ontology reasoning
    :param extra_args:
        Extra positional arguments to pass in the command line
    :param debug:
        Turn on -vvv
    :return: Output from standard out from running ROBOT
    """
    if input_flag is None:
        input_flag = "-I" if _is_remote(input_path) else "-i"

    args: list[str] = []

    if merge and not reason:
        args.extend(["merge", str(input_flag), str(input_path), "convert"])
    elif merge and reason:
        args.extend(
            [
                "merge",
                str(input_flag),
                str(input_path),
                "reason",
                "convert",
            ]
        )
    elif not merge and reason:
        args.extend(
            [
                "reason",
                str(input_flag),
                str(input_path),
                "convert",
            ]
        )
    else:
        args.extend(
            [
                "convert",
                str(input_flag),
                str(input_path),
            ]
        )

    args.extend(("-o", str(output_path)))
    if extra_args:
        args.extend(extra_args)
    if not check:
        args.append("--check=false")
    if fmt:
        args.extend(("--format", fmt))
    if debug:
        args.append("-vvv")

    return call_robot(args)


#: Prefixes that denote remote resources
PROTOCOLS = {
    "https://",
    "http://",
    "ftp://",
    "ftps://",
}


def _is_remote(url: str | Path) -> bool:
    return isinstance(url, str) and any(url.startswith(protocol) for protocol in PROTOCOLS)


class ROBOTError(Exception):
    """Custom error for ROBOT command failures that includes output preview."""

    def __init__(
        self,
        command: list[str],
        return_code: int,
        output: str | None = None,
        stderr: str | None = None,
        preview_length: int = 500,
    ) -> None:
        """Initialize a wrapper around a ROBOT exception.

        :param command: The command that was executed and failed
        :param return_code: The exit code returned by the command
        :param output: The stdout/stderr output from the command execution
        :param preview_length:
            Maximum number of characters to include in the
            error message preview. Default is 500 characters.

        The error message will contain the command, return code, and a preview
        of the output truncated to preview_length characters.
        """
        self.command = command
        self.return_code = return_code
        self.stdout = output or "<no stdout>"
        self.preview_length = preview_length
        self.stderr = stderr or "<no stderr>"

        # Create the error message
        command_str = " ".join(command)
        stdout_preview = indent(shorten(self.stdout, preview_length), "  ")
        stderr_preview = indent(shorten(self.stderr, preview_length), "  ")

        message = (
            f"Command `{command_str}` returned non-zero exit status {return_code}.\n\n"
            f"stderr:\n\n{stderr_preview}"
            f"\n\nstdout:\n\n{stdout_preview}"
        )

        super().__init__(message)
