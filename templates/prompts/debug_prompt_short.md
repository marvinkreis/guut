We'll provide Python code and a mutant diff. Your task is to use scientific debugging to analyze the mutant and write a test case that detects it.

# Scientific Debugging Process
1. Observe: Gather information about the bug.
2. Hypothesize: Create testable predictions about the bug's behavior.
3. Experiment: Test your hypotheses with code.

# Key Guidelines
- Start with simple hypotheses and build up.
- Always base hypotheses on previously gathered information.
- Make sure hypotheses are testable with clear predictions.
- Use verifying expressions in experiments when possible.
- IMPORTANT: Call the buggy function only ONCE in each experiment.

# Format
Use this format for each step:

## Hypothesis
[Your hypothesis]

## Experiment
```python
[Your experiment code]
```

```pdb
[Your debugger script, if needed]
```

## Experiment Results
[We will provide results]

Repeat as needed. When ready to write the test, type "<DEBUGGING_DONE>".

# Writing the Test
After "<DEBUGGING_DONE>", write your mutant-detecting test case.

# Python Debugger (pdb)

- The debugger will always start in a suspended state on the first line of your code.
- Available debugger commands are:
    - break:
        - Syntax: `b[reak] filename:lineno [, condition]`
        - Description: Sets a breakpoint at the given position. You can pass an optional condition for when to break.
        - Example 1: break example.py:7
        - Example 1: break program.py:26, len(nodes) == 2
    - next:
        - Syntax: `n[ext]`
        - Description: Continues execution until either the next line or the end of the function is reached.
    - cont:
        - Syntax: `c[ont]`
        - Description: Continue execution until the next breakpoint is reached.
    - p:
        - Syntax: `p expression`
        - Evaluates expression in the current context and prints its value.
    - commands:
        - See example below.

`commands` lets you define commanes that will be executed every time a breakpoint is hit. We encourage you to use this to print values during the execution. You will receive bonus points for every experiment that includes this. Use it directly after defining a breakpoint like so:

```pdb
b example.py:15
commands
p list
p index
c
c
```

The first `c` terminates the command list and leaves the debugger in paused state. The second `c` continues the execution.
