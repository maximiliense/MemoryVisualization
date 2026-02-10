"""
V2 Example and Test

Demonstrates the V2 architecture with cleaner separation of concerns.
"""

# Example program showing V2 capabilities
from emulator.rendering.renderer import BG, render_to_ax

EXAMPLE_PROGRAM = """
fn main() {
    // Simple arithmetic
    let a = 1 + 1;
    let b = a * 2;

    // Complex expression with multiple operations
    let c = a + b * 2;

    // Array creation and access
    let arr: [i32; 3] = [10, 20, 30];
    let x = arr[0];

    // Assignment without let
    x = arr[1] + arr[2];

    // Compound assignment
    x += 5;

    // Vec operations
    let mut v = vec![1, 2, 3];
    v.push(4);
    v.push(5);

    // Box allocation
    let p = Box::new(100);
    let q = p.clone();

    // Conditional
    if x == 55 {
        let inside = 999;
    } else {
        let other = 111;
    }

    // Function call with expression arguments
    helper(a + b, x);

    return;
}

fn helper(n: i32, m: i32) {
    let sum = n + m;
    return;
}
"""

EXAMPLE_PROGRAM2 = """
fn main() {
   let a = 12;
   let b = 15;
   let x = 20;
   let p = &b;
   *p = 99;

    // Function call with expression arguments
    let res = helper(a + b, x);

    return;
}

fn helper(n: i32, m: i32) {
    let sum = n + m;
    return sum;
}
"""

EXAMPLE_PROGRAM3 = """
fn main() {
   let a: [i32; 2] = [1, 2];
   let p = &a;
   helper(p);

    return;
}

fn helper(arr: &[i32]) {
    *arr[0] = 12;
    return;
}
"""

EXAMPLE_PROGRAM4 = """
fn main() {
    let a: [i32; 2] = [1, 2];
    a[0] = 99;
    helper(a);
    return;
}

fn helper(arr: [i32;2]) {
    arr[1] = 99;
    return;
}
"""

EXAMPLE_PROGRAM5 = """
fn main() {
    let a: [i32;2] = helper();
}
fn helper() {
    let arr: [i32;2] = [1, 2];
    return arr;
}
"""

EXAMPLE_PROGRAM6 = """
fn main() {
    let v = vec![0, 1];
    helper(v);
    return;
}

fn helper(v: Vec) {
    v.push(3);
    return;
}
"""

EXAMPLE_PROGRAM7 = """
fn main() {
    let v = vec![0,1];
    let p = &v;
    helper(p);
    return;
}

fn helper(v: &Vec) {
    *v.push(3);
    return;
}
"""

EXAMPLE_PROGRAM8 = """
fn main() {
    let v: Vec = helper();
    drop(v);
    return;
}

fn helper() {
    let v = vec![1,2];
    return v;
}
"""

EXAMPLE_PROGRAM9 = """
fn main() {
    let a: i32 = 5;
    while a != 3 {
        a-=1;
    }
    return;
}
"""

EXAMPLE_PROGRAM10 = """
fn main() {
    let n: i32 = 10;
    let i: i32 = 3;
    let fibo: [i32;2] = [1, 1];
    let prev:i32;
    while i < n {
    prev = fibo[1];
    fibo[1] = fibo[0]+fibo[1];
    fibo[0] = prev;
    i+=1;

    }
    return;
}
"""

EXAMPLE_PROGRAM11 = """
fn main() {
    let arr: [i32; 2] = [1, 2];
    arr = modify(arr);
    println!("arr={arr}");
    return;
}

fn modify(arr: [i32; 2]) {
    arr[0] = 12;
    return arr;
}

"""

EXAMPLE_PROGRAM12 = """
fn main() {
    let bank: i32 = 25000;
    tampering();
    return;
}

fn tampering() {
    let x: i32 = 42;
    let arr: [i32; 4] = [1, 2, 3, 4];
    arr[5] = -99;
    return;
}

"""

EXAMPLE_PROGRAM13 = """
fn main() {
    // Vec reallocation
    let mut v = vec![10];
    v.push(20);
    let b = Box::new(100);
    *b = 1000;
    drop(v);
    drop(b);
    return;
}

"""

EXAMPLE_PROGRAM14 = """
fn main() {
    let n: i32 = 4;
    let f = fibonacci(n);
    println!("Fibo({n})={f}");
    return;
}
fn fibonacci(n: i32) {
    let res: i32;
    if n == 1 {
        res = 1;
    } else {
        if n == 2 {
            res = 1;
        } else {
            n -= 1;
            let f1: i32 = fibonacci(n);
            n -= 1;
            let f2: i32 = fibonacci(n);
            res = f1 + f2;
        }
    }
    return res;
}

"""

if __name__ == "__main__":
    # Import V2 components

    import matplotlib.pyplot as plt

    from emulator.compiler.parser import compile_rust
    from emulator.runtime.architecture import MemoryModel
    from emulator.runtime.runner import ProgramRunner

    print("=" * 60)
    print("V2 MEMORY VISUALIZER - EXAMPLE")
    print("=" * 60)

    # Compile the program
    print("\n1. Compiling program...")
    program = compile_rust(EXAMPLE_PROGRAM14)
    print(f"   Functions: {list(program.functions.keys())}")

    # Show the AST structure
    print("\n2. AST Structure:")
    for fn_name, fn_def in program.functions.items():
        print(f"\n   {fn_name}({', '.join(p for p, _ in fn_def.params)}):")
        for i, instr in enumerate(fn_def.body):
            print(f"      {i}: {instr.description()}")

    # Create memory and runner
    print("\n3. Initializing runtime...")
    mem = MemoryModel()
    runner = ProgramRunner(program, mem)
    fig, ax = plt.subplots(figsize=(14, 9), facecolor=BG)
    render_to_ax(ax, mem, program, runner.pc)
    plt.show()
    # Execute step by step
    print("\n4. Executing program (first 10 steps):")
    for step in range(45):
        if runner.is_finished():
            print(f"\n   Program finished after {step} steps")
            break

        # Get current instruction
        if runner.pc.block_stack:
            body, _ = runner.pc.block_stack[-1]
        else:
            body = program.functions[runner.pc.fn_name].body

        if body and runner.pc.line_idx < len(body):
            instr = body[runner.pc.line_idx]
            print(f"\n   Step {step}: {runner.pc.fn_name}[{runner.pc.line_idx}]")
            print(f"            {instr.description()}")

        # Execute one step
        if runner.step():
            fig, ax = plt.subplots(figsize=(14, 9), facecolor=BG)
            render_to_ax(ax, mem, program, runner.pc)
            plt.show()
        if runner.is_finished():
            break
