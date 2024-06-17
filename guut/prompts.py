prompt='''Below, you are going to find a python function with a bug, and a diff containing the fix for the bug.
Your job is to use scientific debugging to understand how the bug affects the function.
Once you fully understand the bug, you will be asked to write a unit test that can detect it.


# Scientific Debugging

Scientific debugging helps you solve a problem step-by-step: First, you create a hypothesis that is in line with your current
understanding of the code. Then you make a prediction about how the code will behave if your hypothesis is correct.
Then you perform an experiment to test your prediction, and draw a conclusion from the result. After the conclusion, you are
either done, or you start with a new hypothesis and continue the loop.

It is important that you follow the following steps correctly:

1. Hypothesis
    - Hypotheses provide an explanation for the buggy behavior or provide key insights.
    - Hypotheses are the key aspect of this approach, and should be detailed and written with care.
    - Hypotheses should build upon previous information.
    - Repeating hypothesis is strongly discouraged.

    - Example hypothesis 1: "Given that [information], the method is [overall erroneous behavior]. Specifically, in the buggy version of `example.py`, `c > b` on line 12 never evaluates to True, so the body of the if-condition is never executed. Because of this, [erroneous behavior].
    - Example hypothesis 2: "As the previous hypothesis was rejected, we now that the body of the if-condition is sometimes executed. Seeing that the fix changes `c > b` to `c >= b`, perhaps the loop has an off-by-one error instead, this means that [desired behavior], but instead [erroneous behavior]."
    - Example hypothesis 3: "Because the previous hypothesis was supported, the code [information]. Therefore, calling the function with [test input] will [erroneous behavior]."
    - Example hypothesis 4: "It seems the previous experiment ended in an error. Perhaps the experiment can be refined by [new experiment]."

2. Prediction
    - Predictions describe a specific value or symptom that would be observed if the hypothesis is correct.
    - Depending on the hypothesis, one may make the prediction that:
        - A code snippet would have different output when ran on the buggy version and the fixed version.
        - A debugger would show different variable values or behavior when ran on the buggy version and the fixed version.

    - Example prediction 1: If I use the debugger to stop at line 13, only the fixed version will stop and print, since the line will never be executed in the buggy version.
    - Example prediction 2: If I let the debugger stop at line 24 and print [expr], while given the input and its intended role indicates that its value should be [correct value], it will instead be [erroneous value].
    - Example prediction 3: If I call the function with [bug-revealing input], then the buggy version will return [erroneous output], while the fixed version will return [correct output].
    - Example prediction 4: When the input to the contains [bug-revealing input], then the buggy version will be caught in an infinite loop, while the fixed version will return normally.

3. Experiment
    - Since predictions can't stand on their own, experiments provide a way to verify or falsify your predictions.
    - Each experiment will contain a code snippet, which calls the investigated function.
    - The code snippet will be ran against both the buggy and the correct implementation, and you'll be given both results to draw a conclusion from.
    - Additionally, you can provide a specific python debugger (pdb) script that checks whether the prediction is true. If you provide the debugger script, the code snippet is additionally executed against the buggy and the fixed version in the debugger.

    - Example experiment 1 (test code):
        ```python
            result = example.foo([1,2,3])
            print(result)
            assert 4 not in result
        ```
    - Example experiment 2 (pdb script):
        ```debugger
            b example.py:12
            c
            print [expr]
        ```

4. Conclusion
    - After the experiment concludes, you are given the outputs to draw a conclusion.
    - The conclusion is a judgement whether the hypothesis is true based on the observation.
    - Add <DEBUGGING DONE> when you fully understood the bug and gathered enough information to create a test to detect it.

    - Example observation 1: The hypothesis is supported since the test outputs [erroneous output] for the buggy version.
    - Example observation 2: The hypothesis is rejected, because [reason].
    - Example observation 3: The hypothesis is undecided due to an error in the experiment.


# Debugger (pdb) Explanation

- The debugger will always start in a suspended state on the first line.
- Available debugger commands are:
    - b:
        - Syntax: `b filename:lineno [, condition]`
        - Description: Sets a breakpoint at the given position. If a condition is given, the breakpoint will only stop the execution if the condition evaluates to true.
        - Example 1: b example.py:7
        - Example 1: b program.py:26, len(nodes) == 2
    - n:
        - Syntax: `n`
        - Description: Continues execution until either the next line or the end of the function is reached.
    - unt:
        - Syntax: `unt lineno`
        - Description: Continues execution until the line with the number lineno is reached.
    - c:
        - Syntax: `c`
        - Description: Continue execution until the next breakpoint is reached.
    - p:
        - Syntax: `p expression`
        - Evaluates expression in the current context and prints its value.


# General Procedure

The process will follow this general outline:
- You provide a hypothesis, a prediction and an experiment in your message.
- We give you the experiment's results.
- You respond with a conclusion first. If you choose to continue, also include a new hypothesis, prediction and experiment in your message. If you believe you understand the bug now, include `<DEBUGGING_DONE>` in your message instead.
- After you are done, we provide you with a unit test template. You then use your insights to write a unit test that detects the bug.


# Output format

Output all code in markdown code blocks, and use the language to specify if the code is a python snippet or a debugger snippet. For example:

```python
    // python code here
```

```debugger
    // debugger script here
```

Lead each scientific debugging step with the name of the step and a colon. For example:

Hypothesis:
Prediction:
Experiment:
Conclusion:


# Problem
'''
