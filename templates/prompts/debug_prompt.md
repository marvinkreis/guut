We are going to give you some Python code and a mutant diff. We would like you to use scientific debugging to analyze the mutant diff, and then write a test case that detects the mutant.

# Scientific Debugging

The goal of scientific debugging is to analyze and understand a software bug (here: mutant) via the scientific method. One starts with limited knowledge about the mutant, then creates hypotheses and conducts experiments with code to test them. The hypotheses, whether verified or falsified, then build the basis for new hypotheses until the mutant is understood.

## Go step by step

Firstly, you might already have an intuitive idea about how the mutant affects the code. This is good, but *do not* start out by assuming that your idea is correct. It is good practice to explain your idea, but the next step should be to *test the assumptions* that are the basis of your idea, even if they may seem obvious.

Think of it like constructing a proof for a thesis. You may find that all parts that make up the thesis are correct, but you may also find some to be incorrect, so you adjust your thesis.

The process should loosely follow a loop of:
- Hypothesis
- Predicttion
- Experiment
- Conclusion

## Observe

Stepping through the program with the debugger can be a great first step to find out what is happening. Try putting a breakpoint and printing relevant values to find *infected paths* (execution paths where the mutant diverges from the correct code). You may use your first experiment to explore without a hypothesis.

## Hypothesize

Each time you run the code (i.e. conduct an experiment) you should have a an unproven idea (i.e. a hypothesis) in mind, that you can test with the experiment. Predict what will happen when you run the code, then check if you predicted correctly. Start with simple hypotheses, even if they may seem obvious. Then use what you learned to test your ideas. Ideally, you will end up with a proven explanation for the bug.

Hypotheses are the key aspect of scientific debugging, and should be written detailed and with great care.
- Include a relevant prediction and an experiment with every hypothesis.
- Don't repeat hypotheses you have already made.
- Don't base hypotheses on unproven assumptions. Prove the assumtions first.
- Don't create hypotheses that you already know to be true or false based on previous test output. Study the output closely.

An example hypothesis: I want to find out if [assumption] when [mutant difference]. I predict that [assumed result] and I will verify this by [more explanation and experiment description].

## Experiment

You conduct experiments to observe the program and test your hypotheses. Each experiment will contain a python code snippet that imports and calls the infected code. We will take your code snippet and execute it once on the correct code and once on the mutated code, then give you the output of both executions. Therefore, please use the code normally like below:

```python
# good example
import example from example
output = example(123)
```

This will not work:

```python
# BAD example
import example from example  # import correct code
correct_output = example(123)
import example from example  # import mutant
mutant_output = example(123)
```

This also does not work. Do not do this:
```python
# BAD example
import example from example  # import correct code
correct_output = example(123)

# recreate the mutated code
def mutant(index: int):
    list = []
    # ...

mutant_output = mutant(123)
```

Again, we will execute your code twice (agianst correct code and mutant). *DO NOT UNDER ANY CIRCUMSTANCES IMPORT A MUTANT OR RECREATE THE MUTANT! YOU WILL BE DISQUALIFIED IMMEDIATELY!*

If possible, please include a *verifying expression* in your experiment. A verifying expression is an expression that you print in your experiment to help you to verify the prediction you have made. For example, you predicted that the mutated function always returns the empty list and the correct implementation dosen't, so you include in your experiment: `print("verifying expression: " + (len(example()) == 0))`. Then, your prediction is only confimed if the expression shows `True` in the mutant output and `False` in the correct output. Be sure to explain this in your prediction.

We encourage you to use the python debugger (pdb) to explore the function execution. We recommend creating breakpoint commands that will print relevant values each time the breakpoint is hit. To use the debugger, simply include a pdb script in your experiment like below, and we will execut your python code through the debugger:

```pdb
break example.py:15
commands
p list
p index
cont
cont
```

## Syntax Errors

Sometimes, your experiments will have errors. That's ok. Simply fix the errors as repeat the experiment. You don't have to repeat your hypothesis and prediction.

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
        - Syntax: `break filename:lineno [, condition]`
        - Description: Sets a breakpoint at the given position. You can pass an optional condition for when to break.
        - Example 1: break example.py:7
        - Example 1: break program.py:26, len(nodes) == 2
    - next:
        - Syntax: `next`
        - Description: Continues execution until either the next line or the end of the function is reached.
    - cont:
        - Syntax: `cont`
        - Description: Continue execution until the next breakpoint is reached.
    - p:
        - Syntax: `p expression`
        - Evaluates expression in the current context and prints its value.
    - commands:
        - See example below.

`commands` lets you define commanes that will be executed every time a breakpoint is hit. We encourage you to use this to print values during the execution. Use it directly after defining a breakpoint like so:

```pdb
break example.py:15
commands
p list
p index
cont
cont
```

The first `cont` terminates the command list and the debugger is still in paused state. The second `cont` continues the execution.
