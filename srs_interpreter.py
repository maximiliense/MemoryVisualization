#! /usr/bin/env -S uv run
import argparse

from emulator.compiler.parser import compile_srs
from emulator.runtime.interactive import InteractiveRunner

parser = argparse.ArgumentParser(
    prog="srs_interpreter", description="Compile/run the program and show memory layout"
)


parser.add_argument("filename")

if __name__ == "__main__":
    args = parser.parse_args()
    with open(args.filename) as f:
        text = f.read()
    program = compile_srs(text)
    InteractiveRunner(program)
