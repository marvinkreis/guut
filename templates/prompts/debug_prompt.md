We are going to give you some Python code and a mutant diff. We would like you to use scientific debugging to analyze the mutant diff, and then write a test case that detects the mutant.

# Scientific Debugging

The goal of scientific debugging is to analyze and understand a software bug (here: mutant) via the scientific method. One starts with limited knowledge about the mutant, then creates hypotheses and conducts experiments with code to test them. The hypotheses, whether verified or falsified, then build the basis for new hypotheses until the mutant is understood.

The process should loosely follow a loop of:
- Hypothesis and Prediction
- Experiment
- Conclusion

## Go step by step

Firstly, you might already have an intuitive idea about how the mutant affects the code. This is good, but *do not* start out by assuming that your idea is correct. You should explain your idea, but the next step should be to *test the assumptions* that are the basis of your idea, even if they may seem obvious. Think of it like constructing a proof for a thesis. You may find that some assuptions you made are wrong, so you adjust the thesis or make a new thesis.

## Starting out: Observe

Running the program with the debugger can be a great first step to find out what is happening. Try putting a breakpoint and printing relevant values to find *infected paths* (execution paths where the mutant diverges from the correct code). You may use your first experiment to simply observe, but then you have to use the debugger with at least one "commands" block, for example:

```pdb
b example.py:9
commands
p some_relevant_value
p some_other_value
c
c
```

See "Python Debugger (pdb)" for more information.

## Hypotheses

An hypothesis follows more or less this format: I want to find out if [assumption] when [mutant difference]. I predict that [assumed result] and I will verify this by [more explanation and experiment description].

Start with simple hypotheses, even if they may seem obvious. Then combine what you learned into new ideas. Ideally, you will end up with a proven explanation for the bug.

Each hypothesis must contain a predcition. Predict what will happen when you run the code, then check if you predicted correctly. See "Verifying Expression" for more info.

Hypotheses are the key aspect of scientific debugging, and should be written detailed and with great care.
- Include a relevant prediction and an experiment with every hypothesis.
- Don't repeat hypotheses you have already made.
- Don't base hypotheses on unproven assumptions.

## Experiments

You conduct experiments to observe the program and test your hypotheses. Each experiment will contain a python code snippet that imports and calls the infected code. We will take your code snippet and execute it once on the correct code and once on the mutated code, then give you the output of both executions. Here is an illustrative example:

```python
import gcd from example
output = gcd(25, 5)
print(output)
```

Output of correct code:
```
5
```

Output of mutant:
```
10
```

If possible, please include a *verifying expression* in your experiment. A verifying expression is an expression that you print in your experiment to help you to verify the prediction you have made. For example, you predicted that the mutated function always returns the empty list and the correct implementation dosen't, so you include in your experiment: `print("verifying expression: " + (len(example()) == 0))`. Then, your prediction is only confimed if the expression shows `True` in the mutant output and `False` in the correct output. Be sure to explain this in your prediction.

We encourage you to use the python debugger (pdb) to explore the function execution. We recommend creating breakpoint commands that will print relevant values each time the breakpoint is hit. To use the debugger, simply include a pdb script in your experiment like below, and we will execute your python code through the debugger.

```pdb
b example.py:15
commands
p list
p index
c
c
```

You will receive bonus points for every experiment with a debugger script, but only if it contains a "commands" block, so please remember to include one.

## Experiment Rules

We will run your code against the mutant for you, so please **DO NOT TRY TO CALL THE MUTANT FUNCTION YOURSELF IN THE CODE, OR WE WILL IMMEDIATELY DISQUALFY YOU AND THEN FIRE YOU FROM YOUR JOB**. This means:

1. **DO NOT IMPORT THE FUNCTION TWICE.** This will not work:

```python
import gcd from example  # import correct code
correct_output = gcd(25, 5)
import gcd from example  # import mutant -> WON'T WORK, WE WILL DISQUALFY YOU
mutant_output = gcd(25, 5)
```

2. **THE IMPORTED FUNCTION CAN NOT CHANGE INTO THE MUTANT.** This will not work:

```python
import gcd from example  # import correct code
correct_output = gcd(25, 5)
# this is for the mutant
mutant_output = gcd(25, 5)  # -> WON'T WORK, WE WILL DISQUALFY YOU
```

3. **DO NOT RECREATE THE MUTANT.** We will also disqualify you for this:

```python
import gcd from example  # import correct code
correct_output = gcd(25, 5)

# recreate the mutated code -> NEVER DO THIS, WE WILL DISQUALFY YOU
def gcd_mutant(a: int, b: int):
    # ...

mutant_output = mutant(123)
```

## Syntax Errors

Sometimes, your experiments will have errors. That's ok. Simply fix the errors as repeat the experiment. You don't have to repeat your hypothesis and prediction.

## Conclusions

After every experiment, write a quick conclusion based on the results. Study the experiment results closely, they sometimes tell you more than the outcome of your prediction.

## Finishing the task

Once you understand the bug and what triggers the mutant to behave differently, you can finish debugging and write the mutant-killing test. When you are ready, please write verbatim: `<DEBUGGING_DONE>`. Then you can write the test case. You need to write `<DEBUGGING_DONE>`, so we can see that you are ready.

# Experiment and Test Format

Output all code in markdown code blocks, and specify the language ("python" or "pdb"),
so we can tell which code block is which. For example:

    ```python
    // python code here
    ```

    ```pdb
    // debugger script here
    ```

Make sure to import all necessary functions in the code. You can assume that all python files we give you are in the root directory, so "example.py" would be imported with `import example` or `from example import ...`.

# General Format

Please use this format for every step of your solution:

    ## Hypothesis
    // hypothesis and prediction

    ## Experiment
    // your experiment code

    ## Experiment Results
    // we will give you the results

    ## Conclusion
    // a short conclusion

This will repeat until you write `<DEBUGGING_DONE>`. Also, please include the `## Experiment Results` headline after your experiment so we know that you finished writing your experiment.

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
