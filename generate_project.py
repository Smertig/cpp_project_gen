import pathlib
import shutil
import os
import json
import subprocess
import argparse
import sys

parser = argparse.ArgumentParser(description="Project generator")

parser.add_argument("--compiler", type=str, required=True, help="path to the compiler")
parser.add_argument("--sources", type=int, default=50000, help="number of source files (50000 by default)")
parser.add_argument("--headers", type=int, default=10000, help="number of header files (10000 by default)")
parser.add_argument("--subdirs", type=int, default=250, help="number of sub-directories (250 by default)")
parser.add_argument("--output", type=str, default=None, help="output directory ('.' by default)")
parser.add_argument("--name", type=str, default=None, help="project name (auto-generated by default)")

args = parser.parse_args()

COMPILER_PATH = args.compiler
NUMBER_OF_SOURCES = args.sources
NUMBER_OF_HEADERS = args.headers
SUBDIR_COUNT = args.subdirs
PROJECT_NAME = args.name or f"BigProject_{NUMBER_OF_SOURCES}_{NUMBER_OF_HEADERS}"

SOURCES_PER_DIR = (NUMBER_OF_SOURCES + SUBDIR_COUNT - 1) // SUBDIR_COUNT
HEADERS_PER_DIR = (NUMBER_OF_HEADERS + SUBDIR_COUNT - 1) // SUBDIR_COUNT

ROOT_DIR = pathlib.Path(args.output) if args.output is not None else pathlib.Path.cwd()
PROJECT_DIR = ROOT_DIR / PROJECT_NAME
SOURCES_DIR = PROJECT_DIR / "sources"
INCLUDES_DIR = PROJECT_DIR / "includes"


def get_source_subdir(i: int) -> str:
    return f"subdir_{i // SOURCES_PER_DIR}"


def get_include_subdir(i: int) -> str:
    return f"subdir_{i // HEADERS_PER_DIR}"


def get_source_template(i: int) -> str:
    header_i = i % NUMBER_OF_HEADERS

    return f"""
#include <file_{header_i}.h>

static void test_{i}(int a, int b) {{
  foo_{header_i}(b, a);
}}

    """.strip()


def get_header_template(i: int) -> str:
    return f"""
#pragma once

// Some function
void foo_{i}(int a, int b);

    """.strip()


def generate_sources():
    os.makedirs(SOURCES_DIR)
    all_sources = []
    for i in range(NUMBER_OF_SOURCES):
        subdir = SOURCES_DIR / get_source_subdir(i)
        os.makedirs(subdir, exist_ok=True)
        source_path = subdir / f"file_{i}.cpp"
        with open(source_path, "w") as source:
            source.write(get_source_template(i))
            all_sources.append(source_path)

    return all_sources


def generate_headers():
    os.makedirs(INCLUDES_DIR)
    all_include_dirs = set()
    for i in range(NUMBER_OF_HEADERS):
        subdir = INCLUDES_DIR / get_include_subdir(i)
        os.makedirs(subdir, exist_ok=True)

        all_include_dirs.add(subdir)

        with open(subdir / f"file_{i}.h", "w") as header:
            header.write(get_header_template(i))

    return sorted(all_include_dirs)


def generate_compile_commands(sources: list[pathlib.Path], headers: list[pathlib.Path]):
    include_flags = [f"-I{include_dir.relative_to(PROJECT_DIR).as_posix()}" for include_dir in sorted(headers)]

    with open(PROJECT_DIR / f'compile_commands.json', 'w') as file:
        compile_commands = []
        for source in sources:
            command = [COMPILER_PATH]

            if COMPILER_PATH.endswith("clang-cl.exe"):
                command += ["--driver-mode=cl"]
                command += ["/c"]
                command += [f"/Foobj/{source.relative_to(PROJECT_DIR).as_posix().removesuffix(".cpp")}.obj"]
                command += [f"/Fdobj/{source.relative_to(PROJECT_DIR).as_posix().removesuffix(".cpp")}.pdb"]
                command += include_flags
            else:
                command += ["-c", source.relative_to(PROJECT_DIR).as_posix()]
                command += include_flags

            compile_commands.append({
                "directory": PROJECT_DIR.absolute().as_posix(),
                "command": subprocess.list2cmdline(command),
                "file": source.relative_to(PROJECT_DIR).as_posix()
            })
        json.dump(compile_commands, file, indent=4)


def generate_project():
    print(f"Generating project at {PROJECT_DIR.as_posix()}")

    try:
        if os.path.exists(PROJECT_DIR):
            print("Removing existing project")
            shutil.rmtree(PROJECT_DIR)

        os.makedirs(PROJECT_DIR, exist_ok=True)

        all_sources = generate_sources()
        all_include_dirs = generate_headers()

        generate_compile_commands(all_sources, all_include_dirs)
    except:
        print("Project generation failed, cleaning up...")
        shutil.rmtree(PROJECT_DIR, ignore_errors=True)
        raise


def main() -> int:
    if not os.path.isfile(COMPILER_PATH):
        print(f"No compiler at {COMPILER_PATH}")
        return 1

    generate_project()
    return 0


if __name__ == "__main__":
    sys.exit(main())
