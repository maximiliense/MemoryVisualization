import argparse

from visualizer.compiler import compile_rust
from visualizer.runner import InteractiveRunner

parser = argparse.ArgumentParser(
    prog="srs_interpreter", description="Compile/run the program and show memory layout"
)


parser.add_argument("filename")

if __name__ == "__main__":
    args = parser.parse_args()
    with open(args.filename) as f:
        text = f.read()
    program = compile_rust(text)
    InteractiveRunner(program)
