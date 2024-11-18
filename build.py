#!/usr/bin/env python3

import argparse
import re
import shutil
import sys
from pathlib import Path

from tools.autd3_build_utils.autd3_build_utils import (
    BaseConfig,
    err,
    fetch_submodule,
    rremove,
    run_command,
    substitute_in_file,
    working_dir,
)


class Config(BaseConfig):
    target: str | None
    no_examples: bool

    def __init__(self, args) -> None:  # noqa: ANN001
        super().__init__(args)

        self.no_examples = getattr(args, "no_examples", False)
        self.features = getattr(args, "features", "") or ""

        arch: str = getattr(args, "arch", None)
        if arch:
            if self.is_linux():
                match arch:
                    case "arm32" | "armv7":
                        self.target = "armv7-unknown-linux-gnueabihf"
                    case "aarch64":
                        self.target = "aarch64-unknown-linux-gnu"
                    case "x64":
                        self.target = None
                    case _:
                        err(f'arch "{arch}" is not supported.')
                        sys.exit(-1)
            elif self.is_windows():
                match arch:
                    case "aarch64":
                        self.target = "aarch64-pc-windows-msvc"
                    case "x64":
                        self.target = None
                    case _:
                        err(f'arch "{arch}" is not supported.')
                        sys.exit(-1)
            else:
                self.target = None
        else:
            self.target = None

        self.setup_linker()

    def cargo_command(self, subcommands: list[str]) -> list[str]:
        command = []
        if self.target is None:
            command.extend(["cargo", *subcommands])
        else:
            if self.is_linux():
                command.extend(["cross", *subcommands])
            else:
                command.extend(["cargo", *subcommands])
            command.extend(["--target", self.target])
        if self.release:
            command.append("--release")
        command.extend(["--features", self.features])
        return command

    def setup_linker(self) -> None:
        if not self.is_linux() or self.target is None:
            return
        Path(".cargo").mkdir(exist_ok=True)
        with Path(".cargo/config").open("w") as f:
            if self.target == "armv7-unknown-linux-gnueabihf":
                f.write("[target.armv7-unknown-linux-gnueabihf]\n")
                f.write('linker = "arm-linux-gnueabihf-gcc"\n')
            if self.target == "aarch64-unknown-linux-gnu":
                f.write("[target.aarch64-unknown-linux-gnu]\n")
                f.write('linker = "aarch64-linux-gnu-gcc"\n')


def copy_dll(config: Config, dst: str) -> None:
    path = Path.cwd()
    target: str
    if config.target is None:
        target = "target/release" if config.release else "target/debug"
    else:
        target = f"target/{config.target}/release" if config.release else f"target/{config.target}/debug"
    if config.is_windows():
        for dll in path.glob(f"{target}/*.dll"):
            shutil.copy(dll, dst)
        for lib in path.glob(f"{target}/*.dll.lib"):
            shutil.copy(lib, dst)
    elif config.is_macos():
        for lib in path.glob(f"{target}/*.dylib"):
            shutil.copy(lib, dst)
    elif config.is_linux():
        for lib in path.glob(f"{target}/*.so"):
            shutil.copy(lib, dst)


def copy_lib(config: Config, dst: str) -> None:
    path = Path.cwd()
    target: str
    if config.target is None:
        target = "target/release" if config.release else "target/debug"
    else:
        target = f"target/{config.target}/release" if config.release else f"target/{config.target}/debug"
    if config.is_windows():
        for dll in path.glob(f"{target}/*.lib"):
            shutil.copy(dll, dst)
        rremove(f"{dst}/*.dll.lib")
        if not config.release:
            for pdb in path.glob(f"{target}/*.pdb"):
                shutil.copy(pdb, "lib")
    else:
        for lib in path.glob(f"{target}/*.a"):
            shutil.copy(lib, dst)


def capi_build(args) -> None:  # noqa: ANN001
    config = Config(args)
    run_command(config.cargo_command(["build", "--locked"]))
    Path("bin").mkdir(exist_ok=True)
    copy_dll(config, "bin")
    Path("lib").mkdir(exist_ok=True)
    copy_lib(config, "lib")


def capi_lint(args) -> None:  # noqa: ANN001
    config = Config(args)
    command = config.cargo_command(["clippy"])
    command.extend(["--tests", "--", "-D", "warnings"])
    run_command(command)


def capi_clear(_) -> None:  # noqa: ANN001
    run_command(["cargo", "clean"])


def util_update_ver(args) -> None:  # noqa: ANN001
    version = args.version
    substitute_in_file(
        "Cargo.toml",
        [
            (r'^version = "(.*?)"', f'version = "{version}"'),
            (r'^autd3(.*)version = "=(.*?)"', f'autd3\\1version = "={version}"'),
        ],
        flags=re.MULTILINE,
    )
    substitute_in_file(
        "ThirdPartyNotice.txt",
        [(r"^autd3(.*) (.*) \((.*)\)", f"autd3\\1 {version} (\\3)")],
        flags=re.MULTILINE,
    )
    run_command(["cargo", "update"])


def util_check_license(_) -> None:  # noqa: ANN001
    run_command(["cargo", "update"])
    with working_dir("tools/license-checker"):
        run_command(["cargo", "r"])


def command_help(args) -> None:  # noqa: ANN001
    print(parser.parse_args([args.command, "--help"]))


if __name__ == "__main__":
    with working_dir(Path(__file__).parent):
        fetch_submodule()

        parser = argparse.ArgumentParser(description="autd3capi library build script")
        subparsers = parser.add_subparsers()

        # build
        parser_build = subparsers.add_parser("build", help="see build -h`")
        parser_build.add_argument("--release", action="store_true", help="release build")
        parser_build.add_argument("--arch", help="cross-compile for specific architecture")
        parser_build.add_argument("--features", help="features to build", default=None)
        parser_build.set_defaults(handler=capi_build)

        # lint
        parser_lint = subparsers.add_parser("lint", help="see lint -h`")
        parser_lint.add_argument("--release", action="store_true", help="release build")
        parser_lint.add_argument("--features", help="features to build", default=None)
        parser_lint.set_defaults(handler=capi_lint)

        # clear
        parser_capi_clear = subparsers.add_parser("clear", help="see `clear -h`")
        parser_capi_clear.set_defaults(handler=capi_clear)

        # util
        parser_util = subparsers.add_parser("util", help="see `util -h`")
        subparsers_util = parser_util.add_subparsers()

        # util update version
        parser_util_upver = subparsers_util.add_parser("upver", help="see `util upver -h`")
        parser_util_upver.add_argument("version", help="version")
        parser_util_upver.set_defaults(handler=util_update_ver)

        # util check license
        parser_util_check_license = subparsers_util.add_parser("check-license", help="see `util check-license -h`")
        parser_util_check_license.set_defaults(handler=util_check_license)

        # help
        parser_help = subparsers.add_parser("help", help="see `help -h`")
        parser_help.add_argument("command", help="command name which help is shown")
        parser_help.set_defaults(handler=command_help)

        args = parser.parse_args()
        if hasattr(args, "handler"):
            args.handler(args)
        else:
            parser.print_help()
