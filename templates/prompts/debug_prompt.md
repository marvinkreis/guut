We are going to give you some Python code and a mutant diff. We would like you to use scientific debugging to analyze the mutant diff, and then write a test case that detects the mutant.

# Scientific Debugging

The goal of scientific debugging is to analyze and understand a software bug (here: mutant) via the scientific method. One starts with limited knowledge about the mutant, then creates hypotheses and conducts experiments with code to test them. The hypotheses, whether verified or falsified, then build the basis for new hypotheses until the mutant is understood.

## Go step by step

Firstly, you might already have an intuitive idea about how the mutant affects the code. This is good, but *do not* start out by assuming that your idea is correct. It is good practice to explain your idea, but the next step should be to *test the assumptions* that are the basis of your idea, even if they may seem obvious.

Think of it like constructing a proof for your thesis. You may find that all parts that make up the thesis are correct, but you may also find some to be incorrect, so you adjust your thesis.

## Observe

Wheter or not you already have an idea, stepping through the program with the debugger can be a great tool to find out what is happening. Try putting a breakpoint and printing relevant values to find *infected paths* (execution paths where the mutant diverges from the correct code).

## Hypothesize

Each time you run the code (i.e. conduct an experiment) you should have a an unproven idea (i.e. a hypothesis) in mind, that you can test with the experiment. Predict what will happen when you run the code, then check if you predicted correctly. Start with simple hypotheses, even if they may seem obvious. Then use what you learned to test your ideas. Ideally, you will end up with a proven explanation for the bug.

Hypotheses are the key aspect of scientific debugging, and should be written detailed and with great care.
- Include a relevant prediction and an experiment with every hypothesis.
- Don't repeat hypotheses you have already made.
- Don't base hypotheses on unproven assumptions. Prove the assumtions first.

An example hypothesis: I want to find out if [assumption] when [mutant difference]. I predict that [assumed result] and I will verify this by [more explanation and experiment description].

## Experiment

You conduct experiments to observe the program and to test your hypotheses. Each experiment will contain a python code snippet that imports and calls the mutated code.

You can also use the python debugger (pdb). To use the debugger, simply include a pdb script in your experiment.

Once you stated your experiment, we will take your code and execute it once against the correct version of the function, and once against the mutant.

You'll receive bonus points if you include a *verifying expression*. A verifying expression is a boolean expression that you print in your experiment. It represents the prediction you made in you hypothesis, and its value determines whether the experiment is a success or a failure. For example: You predict in your hypothesis, that the returned list of the function `example` is empty for the correct function but not for the mutant. So you include in your experiment: `print("verifying expression: " + (len(example()) == 0))`. Then, if the expression shows `True` in the correct output and `False` in the mutant output, you'll know that the experiment was successful, and otherwise it was not.

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
