We are going to give you some Python code and a mutant diff. We would like you to use scientific debugging to analyze the mutant diff, and then write a test case that detects the mutant. But first, we'll give you some information on scientific debugging and on how to complete the task.

# Scientific Debugging

The goal of scientific debugging is to analyze and understand a software bug (here: mutant) via the scientific method. One starts with limited knowledge about the bug, then creates hypotheses and conducts experiments to test them. The hypotheses, whether verified or falsified, then build the basis for new hypotheses until the bug is understood.

The next part provides more information about the steps of scientific debugging.

## Starting out

Firstly, you might already have an idea in mind about how the entire bug works. *DO NOT IMMEDIATELY ASSUME THAT IS IDEA IS CORRECT*. It is imperative to this approach that you start with small hypotheses and build your way up. You can write you idea down, but you need to start with smaller hypotheses, even if they seem obvious.

## Observe

The first step is usually to gather information about the bug, so that a hypothesis can be constructed. Try calling the buggy function and printing the output, then check for any difference in behavior between the correct version and the mutant. Bonus points if you use the debugger to print out intermediate values from the computation.

## Hypothesize

The goal of a hypothesis is to get you closer to understanding the bug. Start with simple hypotheses, even if they seem obvious to you. Then combine the gained information to construct more complex hypotheses. Ideally, you will end up with a plausible explanation for the bug. Importantly, *hypotheses are always based on information that have previously been gathered*. One cannot create hypotheses based on untested assumptions.

Hypotheses are the key aspect of scientific debugging, and should be written detailed and with great care. But most importantly, *hypotheses always need to be testable*. Each hypothesis you make needs to come with a prediction. You provide some input to the buggy function and predict how it will behave.

## Experiment

You must conduct experiments to test you predictions. Each experiment will contain a python code snippet that imports and calls the buggy function. You can also use the python debugger (pdb). To use the debugger, simply include a pdb script in your experiment.

Once you stated your experiment, we will take your code and execute it once against the correct version of the function, and once against the mutant.

You'll recieve bonus points if you include a *verifying expression*. A verifying expression is a boolean expression that you print in your experiment. It represents the prediction you made in you hypothesis, and its value determines whether the experiment is a success or a failure. For example: You predict in your hypothesis, that the returned list of the function `example` is empty for the correct function but not for the mutant. So you include in your experiment: `print("verifying expression: " + (len(example()) == 0))`. Then, if the expression shows `True` in the correct output and `False` in the mutant output, you'll know that the experiment was successful, and otherwise it was not.

### Example experiment

Here is an example experiment to help you understand the format better:

    ## Experiment

    ```python
    from example import example

    output = example()
    verifying_expression = (len(output) == 0)
    print(output)
    print(f"verifying expression: {verifying_expression}")
    ```

    ```pdb
    break example.py:14
    cont
    p some_value
    ```

    ## Experiment Results

    Test on correct code:
    ```
    []
    verifying expression: True
    ```

    Test on mutant:
    ```
    [1]
    verifying expression: False
    ```

    Debugger on correct code:
    ```
    > /mnt/temp/test.py(1)<module>()
    -> from example import example
    (Pdb) break example.py:14
    Breakpoint 1 at /mnt/temp/example.py:14
    (Pdb) cont
    > /mnt/temp/example.py(14)example()
    -> return left
    (Pdb) p some_value
    1
    (Pdb)
    ```

    Debugger on mutant:
    ```
    > /mnt/temp/test.py(1)<module>()
    -> from example import example
    (Pdb) break example.py:14
    Breakpoint 1 at /mnt/temp/example.py:14
    (Pdb) cont
    > /mnt/temp/example.py(14)example()
    -> return left
    (Pdb) p some_value
    2
    (Pdb)
    ```

### Important note

*THIS IS VERY IMPORTANT:*  Your code snippet must call the buggy function only once! We will execute it against the correct code and the buggy code for you! Calling the buggy function multiple times in your experiment will result in *immediate disqualification*.

- *DO NOT* recreate the mutant in your experiment.
- *DO NOT* execute the function for both the correct code and the mutant code in your experiment.

#### Example 1
*BAD*:
```python
print("output of the correct version: {example()}")
print("output of the mutant: {example()}")
```

*GOOD*:
```python
print("output: {example()}")
```

#### Example 2

*BAD*:
```python
output_correct = example()
output_mutant = example()
```
*GOOD*:
```python
output = example()
```

#### Example 3

*BAD*:
```python
# We recreate the mutated function
def example():
    ...
```

## Finishing the task

Once you understand the bug and you what inputs cause the correct code and the mutant code to behave differently, you can finish debugging and write the mutant-killing test. When you are ready, please write verbatim: "<DEBUGGING_DONE>". Then you can write the test case. Remember: write "<DEBUGGING_DONE>" when you're ready to write the test.

# Experiment and Test Format

Output all code in markdown code blocks, and specify the language ("python" or "pdb"),
so we can tell which code block is which. For example:

    ```python
    // python code here
    ```

    ```pdb
    // debugger script here
    ```

Make sure to import all necessary functions in the code. You can assume that all python files we give you are in the root directory, so, for example, "example.py" can be imported with `import example` or `from example import ...`.

# General Format

Please use this format for every step of your solution:

    ## Hypothesis
    // hypothesis here

    ## Experiment
    // experiment here

    ## Experiment Results
    // we will give you the results here

Repeat this for every hypothesis you make. Once you are ready to write the test, write verbatim "<DEBUGGING_DONE>".

# Python Debugger (pdb)

- The debugger will always start in a suspended state on the first line of your code.
- Available debugger commands are:
    - break:
        - Syntax: `break filename:lineno [, condition]`
        - Description: Sets a breakpoint at the given position. You can pass an optional condition for when to break.
        - Example 1: break example.py:7
        - Example 1: break program.py:26, len(nodes) == 2
    - next:
        - Syntax: `next`
        - Description: Continues execution until either the next line or the end of the function is reached.
    - until:
        - Syntax: `until lineno`
        - Description: Continues execution until the line with the number lineno is reached.
    - cont:
        - Syntax: `cont`
        - Description: Continue execution until the next breakpoint is reached.
    - p
        - Syntax: `p expression`
        - Evaluates expression in the current context and prints its value.

# Task

{problem}

# Scientific debugging
