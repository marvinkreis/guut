We are going to give you a Python program and a mutant diff. We want you to use scientific debugging to understand the mutant diff, and then write a test case that detects the mutant.


# Scientific Debugging

Scientific debugging is a sytstematic debugging approach based on the scientific method. The process follows a loop of:

- Observation
- Hypothesis
- Experiment
- Conclusion

## Observation

In the beginning, please run the code with a debugger script to get a good idea of what is happening in the code. Put a breakpoint and print relevant values to find *infected paths* (execution paths where the mutant diverges from the correct code).

### Example Observation

Consider the following example program that implements the sieve of Eratosthenes. We will refer back to this later:

```python sieve.py
1  def sieve(max):
2      primes = []
3      for n in range(2, max + 1):
4          if all(n % p > 0 for p in primes):
5              primes.append(n)
6      return primes
```

```diff mutant.diff
diff --git a/sieve.py b/sieve.py
index d9a0df7..3125b92 100644
--- a/sieve.py
+++ b/sieve.py
@@ -1,6 +1,6 @@
 def sieve(max):
     primes = []
     for n in range(2, max + 1):
-        if all(n % p > 0 for p in primes):
+        if any(n % p > 0 for p in primes):
             primes.append(n)
     return primes
```

The initial initial observation step could look like this:

```python
from sieve import sieve
from mutant.sieve import sieve as sieve_mutant

print(f"Correct output: {sieve(5)}")
print(f"Mutant output: {sieve_mutant(5)}")
```

```pdb
b sieve.py:5
commands
print(f"without mutant: n={n}, primes={primes}")
c
b mutant/sieve.py:5
commands
print(f"with mutant: n={n}, primes={primes}")
c
c
```

And it would yield the following output:

Script output
```
Correct output: [2, 3, 5]
Mutant output: []
```

Debugger output:
```
> test.py(1)<module>()
-> from sieve import sieve
(Pdb) b sieve.py:5
Breakpoint 1 at sieve.py:5
(Pdb) commands
(com) p f"without mutant: primes={primes}, n={n}"
(com) c
(Pdb) b mutant/sieve.py:5
Breakpoint 2 at mutant/sieve.py:5
(Pdb) commands
(com) p f"with mutant: primes={primes}, n={n}"
(com) c
(Pdb) c
without mutant: primes=[], n=2
> sieve.py(5)sieve()
-> primes.append(n)
without mutant: primes=[2], n=3
> sieve.py(5)sieve()
-> primes.append(n)
without mutant: primes=[2, 3], n=5
> sieve.py(5)sieve()
-> primes.append(n)
Correct output: [2, 3, 5]
Mutant output: []
The program exited.
```

Here, for example, you would see that line 5 is executed normally without the mutant, but isn't executed at all with the mutant in place.

See "Python Debugger (pdb)" for more information.

## Hypothesis

Each hypothesis should describe an assumption you have about the code. You predict what will happen when you run the code in your experiment, then check if you predicted correctly.

Hypotheses are the key aspect of scientific debugging, and should be written detailed and with great care.
- Base hypotheses on the findings of previous experiments.
- Include a relevant prediction and an experiment with every hypothesis.
- Don't repeat hypotheses you have already made.
- Don't base hypotheses on untested assumptions.

Hypotheses follow this template: I hypothesize that [assumption] holds when [mutant difference]. I predict that [assumed result] and I will verify this by [more explanation and experiment description].

### Example Hypothesis

The observation step showed that the mutant didn't call the `append` function and returned an empty list. Therefore, I hypothesize that the mutant will also output an empty list for a different input n=10. I will verify this by calling both versions of sieve with n=10 and checking that the mutant outputs the empty list, while the correct code doesn't.

## Experiment

Each experiment will contain python code that imports and calls the correct code and the mutant. We will then execute that code for you and give you the results.

- Use the debugger to print out intermediate values. Simply include a pdb script in the experiment.
- Don't forget to print your outputs.
- Make sure to import all necessary functions. You can assume that all python files we give you are in the root directory, and the mutant is in the "mutant" directory.
- Sometimes, an experiments will have syntax errors. Then, please fix the errors as repeat the experiment. Don't repeat your hypothesis and prediction.

### Example Experiment

```python
from sieve import sieve
from mutant.sieve import sieve as sieve_mutant

output_correct = sieve(10)
output_mutant = sieve_mutant(10)

print(f"Correct output: {output_correct}")
print(f"Mutant output: {output_mutant}")
print(f"Verifying expression: {len(output_mutant) == 0 and len(output_correct) > 0}")
```

```pdb
b sieve.py:5
commands
print(f"without mutant: n={n}, primes={primes}")
c
b mutant/sieve.py:5
commands
print(f"with mutant: n={n}, primes={primes}")
c
c
```

This would yield the following output:

Script output:
```
Correct output: [2, 3, 5, 7]
Mutant output: []
Verifying expression: True
```

TODO
TODO
TODO
TODO
TODO
TODO

## Conclusion

After every experiment, write a conclusion that summarizes on the results. Examine the experiment results closely so you don't miss anthing. Keep the conclusions brief, so you can refer back to them easily.

### Example Conclusion

We can see that for n=10, the mutant returned an empty list and the correct code returned prime numbers. The verifying expression also evaluated to `True`. Therefore we can confirm the hypothesis.

## Test

Keep writing new hypotheses and testing them until you understand the muntant. Once you have understood the mutant, you can finish debugging and write the mutant-killing test.

The test is different that an experiment. In the test, you don't import the mutant. Instead you write a test that passes on the correct code and fail when executed against the mutant.

Output the test as a simple python snippet. Don't use any functions or testing frameworks.

### Example Test

```python
from sieve import sieve

output = sieve(10)
assert len(output) > 0, "sieve must output prime numbers"
```


# Output Format

Please use this format for your solution:

    # Task
    [we give you the code and the mutant]

    # Debugging

    ## Observation
    [your observation code]

    ### Observation Results
    [we will give you the observation results]

    ## Hypothesis
    [hypothesis and prediction]

    ### Experiment
    [your experiment code]

    ### Experiment Results
    [we will give you the results]

    ### Conclusion
    [a short conclusion]

    [more hypotheses until you are ready to write the mutant-killing test]

    # Test
    [the mutant-killing test]

    ## Test Results
    [we will give you the results]

Write all code in markdown blocks and specify the language, e.g.:

    ```python
    // python code here
    ```

    ```pdb
    // debugger script here
    ```

Be brief in your responses and don't repeat things you have already written. Write brief hypotheses and conclusions makes it easier to refer back to them later.


# Python Debugger (pdb)

- The debugger will always start in a suspended state on the first line of your code.
- Available debugger commands are:
    - break:
        - Syntax: `b[reak] filename:lineno [, condition]`
        - Description: Sets a breakpoint at the given position. You can pass an optional condition for when to break.
        - Example 1: break mutant/sieve.py:5
        - Example 1: break sieve.py:5, len(primes) != 0
      - commands:
        - Syntax: `commands \n <your commands> \n [end|c]`
          - `commands` lets you define commands that will be executed every time a breakpoint is hit.
    - next:
        - Syntax: `n[ext]`
        - Description: Continues execution until either the next line or the end of the function is reached.
    - cont:
        - Syntax: `c[ont]`
        - Description: Continue execution until the next breakpoint is reached.
    - print():
        - Syntax: `print(expression)`
        - Evaluates expression in the current context and prints its value.
    - dir():
        - Syntax: `dir(expression)`
        - Evaluates expression in the current context and prints its value.

We encourage you to use the `commands` command to print out intermediate values. You will receive bonus points for every experiment that includes a debugger script with `commands`. Use it directly after defining a breakpoint like so:

```pdb
b sieve.py:5
commands
print(f"without mutant: n={n}, primes={primes}")
c
b mutant/sieve.py:5
commands
print(f"with mutant: n={n}, primes={primes}")
c
c
```

In this example, the `c` command terminates the command list and instructs the debugger to continue execution after the command list ended. This leaves the debugger in paused state. A second `c` then continues the execution.
