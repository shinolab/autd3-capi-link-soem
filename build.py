#!/usr/bin/env python3

import argparse
import re
import shutil
import sys
from pathlib import Path

from tools.autd3_build_utils.autd3_build_utils import (
    BaseConfig,
    err,
    rm_glob_f,
    run_command,
    working_dir,
)


class Config(BaseConfig):
    _all: bool
    release: bool
    target: str | None
    no_examples: bool

    def __init__(self, args) -> None:
        super().__init__()

        self._all = hasattr(args, "all") and args.all
        self.release = hasattr(args, "release") and args.release
        self.no_examples = hasattr(args, "no_examples") and args.no_examples
        self.features = args.features if hasattr(args, "features") and args.features else ""

        if hasattr(args, "arch") and args.arch is not None:
            if self.is_linux():
                match args.arch:
                    case "arm32" | "armv7":
                        self.target = "armv7-unknown-linux-gnueabihf"
                    case "aarch64":
                        self.target = "aarch64-unknown-linux-gnu"
                    case "x64":
                        self.target = None
                    case _:
                        err(f'arch "{args.arch}" is not supported.')
                        sys.exit(-1)
            elif self.is_windows():
                match args.arch:
                    case "aarch64":
                        self.target = "aarch64-pc-windows-msvc"
                    case "x64":
                        self.target = None
                    case _:
                        err(f'arch "{args.arch}" is not supported.')
                        sys.exit(-1)
            else:
                self.target = None
        else:
            self.target = None

        self.setup_linker()

    def cargo_command(self, subcommands: list[str]) -> list[str]:
        command = []
        if self.target is None:
            command.append("cargo")
            command.extend(subcommands)
        else:
            if self.is_linux():
                command.append("cross")
                command.extend(subcommands)
            else:
                command.append("cargo")
                command.extend(subcommands)
            command.append("--target")
            command.append(self.target)
        command.append("--all")
        if self.release:
            command.append("--release")
        command.append("--features")
        command.append(self.features)
        if "static" in self.features or "unity" in self.features:
            command.append("--exclude")
            command.append("autd3capi-emulator")
        return command

    def setup_linker(self):
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
        rm_glob_f(f"{dst}/*.dll.lib")
        if not config.release:
            for pdb in path.glob(f"{target}/*.pdb"):
                shutil.copy(pdb, "lib")
    else:
        for lib in path.glob(f"{target}/*.a"):
            shutil.copy(lib, dst)


def capi_build(args) -> None:
    config = Config(args)

    run_command(config.cargo_command(["build"]))

    Path("bin").mkdir(exist_ok=True)
    copy_dll(config, "bin")
    Path("lib").mkdir(exist_ok=True)
    copy_lib(config, "lib")


def capi_lint(args) -> None:
    config = Config(args)

    command = config.cargo_command(["clippy"])
    command.append("--tests")
    command.append("--")
    command.append("-D")
    command.append("warnings")
    run_command(command)


def capi_clear(_) -> None:
    run_command(["cargo", "clean"])


def util_update_ver(args) -> None:
    version = args.version

    with Path("Cargo.toml").open() as f:
        content = f.read()
        content = re.sub(
            r'^version = "(.*?)"',
            f'version = "{version}"',
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r'^autd3(.*)version = "(.*?)"',
            f'autd3\\1version = "{version}"',
            content,
            flags=re.MULTILINE,
        )
    with Path("Cargo.toml").open("w") as f:
        f.write(content)

    with Path("ThirdPartyNotice.txt").open() as f:
        content = f.read()
        content = re.sub(
            r"^autd3(.*) (.*) \((.*)\)",
            f"autd3\\1 {version} (MIT)",
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r"^autd3-link-twincat (.*)",
            f"autd3-link-twincat {version}",
            content,
            flags=re.MULTILINE,
        )
    with Path("ThirdPartyNotice.txt").open("w") as f:
        f.write(content)

    run_command(["cargo", "update"])


def util_check_license(_) -> None:
    run_command(["cargo", "update"])
    with working_dir("tools/license-checker"):
        run_command(["cargo", "r"])


def command_help(args) -> None:
    print(parser.parse_args([args.command, "--help"]))


if __name__ == "__main__":
    with working_dir(Path(__file__).parent):
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
