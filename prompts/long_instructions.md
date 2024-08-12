# Instructions

Below, you will find a python function and a mutant diff. Your task is to use the scientific method to understand how the bug affects the function. We will then ask you to write a unit test that can detect the bug. It is important that you follow the following steps correctly and in order:

## 1. Hypothesis
- Hypotheses provide a potential explanation for the buggy behavior based on your current understanding and previous hypotheses.
- Hypotheses are the key aspect of this approach, and should be as detailed as possible.

- Example hypothesis 1: "Given that [information], the method [erroneous behavior]. Specifically, in the buggy version of `example.py`, `c > b` on line 12 never evaluates to True, so the body of the if-condition is never executed. Because of this, [erroneous behavior].
- Example hypothesis 2: "As the previous hypothesis was rejected, we now that the body of the if-condition is sometimes executed. Seeing that the fix changes `c > b` to `c >= b`, perhaps the loop has an off-by-one error instead, this means that [desired behavior], but instead [erroneous behavior]."
- Example hypothesis 3: "It seems the previous experiment ended in an error. Perhaps the experiment can be refined by [new experiment]."

## 2. Prediction
- Predictions describe a specific symptom that would be observed if the hypothesis is correct.
- Depending on the hypothesis, one may make the prediction that:
    - A test case would pass on fixed version but fail on the buggy version.
    - Running a debugger on the buggy version and the fixed version would show different behaviour.
- Your prediction MUST contain a *verifying condition*, meaning a boolean expression that helps you decide whether the prediction is correct.

- Example prediction 1: If I call the function with [bug-revealing input], then the buggy version will return [erroneous output], while the fixed version will return [correct output]. Therefore, I will add an assertion that checks [condition].
- Example prediction 2: If I use the debugger to stop at line 13, the list will not be initialized yet, since the if condition never evaluates to True in the buggy version. I will check if the list is still empty here.
- Example prediction 3: If I let the debugger stop at line 24 and print [expr], while given the input and its intended role indicates that its value should be [correct value], it will instead be [erroneous value].

## 3. Experiment
- Experiments exist to test your predictions.
- Each experiment will contain a test case that calls the investigated function.
- The test case will be ran against both the buggy version and the correct version, and you'll be given the output of both runs to draw a conclusion from.
- Additionally, you should provide a python debugger (pdb) script. The test case will then be executed in the debugger with your script.
- It is imperative to include an assertion that checks your *verifying condition*. Without an assertion, your test case will not be accepted. In the debugger script, make sure to print the *verifying condition*.
- Printing the output of the function is encouraged, since it aids in understanding the bug.

- Example experiment 1 (test code):
```python
from example import example

result = example.foo([1,2,3])
print(result)
assert 4 not in result  # verifying condition
```
- Example experiment 2 (test code):
```python
from example import example

user = example.bar('user', 'password', 123)
print(user)
assert user.name == 'user'  # verifying condition
```
- Example experiment 3 (pdb script):
```debugger
b example.py:12
c
print vals
print len(vals) > 5  # verifying condition
```
- Example experiment 4 (pdb script):
```debugger
b example.py:5, n > 7
c
print n
print p
c
print n
print p
print p < 0  # verifying condition
```

## 4. Experiment Results
- After you've stated your experiment, we will execute it and give you back the results.
- Do not write the experiment results yourself.



## 5. Conclusion
- After the experiment concludes, you are given the outputs to draw a conclusion. - The conclusion is a judgement whether the hypothesis is true based on the observation.
- Use the *verifying condition* to tell if the experiment was a success. Only accept the hypothesis if your assertion passed for the correct version.
- If the outcome of the experiment is unclear, it is encouraged to try again with a refined hypothesis. Only verify the hypothesis if you are sure.
- Write <DEBUGGING DONE> verbatim after your conclusion when you gathered enough information to create a test that detects the bug.

- Example observation 1: The hypothesis is supported since the assertion passed for the correct version but failed on the buggy version.
- Example observation 2: The hypothesis is rejected, because the assertion was supposed to fail on the buggy version and didn't.
- Example observation 3: The hypothesis is rejected, because the verifying condition evaluated to False when debugging the correct version.
- Example observation 3: The hypothesis is undecided due to an error in the experiment.


## Python Debugger (pdb)

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


## Output format

Output all code in markdown code blocks, and use the language to specify if the code is a test case or a debugger script. For example:

```python
// python code here
```

```debugger
// debugger script here
```

Make sure to import all necessary functions in the code.

Lead each scientific debugging step with the name of the step and a colon, like this:

Hypothesis:
Prediction:
Experiment:
Experiment Result:
Conclusion:

# Task

{problem}

# Debugging
