I want you to use the scientific method to generate a mutant-killing test case by describing the hypothesis/prediction/experiment/observation/conclusion. This can be done by:
Hypothesis: An explanation for the mutant's survival. Hypotheses are the key aspect of the approach, and should be detailed and written with care. Hypotheses should build upon all previous information; repeating previous hypotheses
is thus strongly discouraged. Some examples are provided below.
- Example hypothesis 1: Given that [reason why the mutant survived], the test suite is missing [description of the lacking test case].
Specifically, I think it is because ‘c>b‘ on line 100 of method ‘foo‘ is never tested with a value of c == b.
- Example hypothesis 2: As the previous hypothesis was rejected, we now know a lack of testing for c == b  for line 4321 of the method
‘foo‘ is likely not the culprit. Looking elsewhere, perhaps we should add a test that covers ‘x.append(y)‘.
- Example hypothesis 3: Because the previous hypothesis was supported, I think updating the test code to cover the scenario where c == b may kill the mutant.
- Example hypothesis 4: It seems the previous experiment ended in an error, we may need to try a different experiment. Perhaps the experiment can be refined by [new experiment].
Prediction: A specific value or symptom that would be observed if the hypothesis is correct. The prediction is that the test code should fail and therefore kill the mutant.
- Example prediction 1: If I change [expr] to [new_expr], the test will fail.
- Example prediction 2: If I change the code to utilize the new variable, the test will fail.
Experiment: A complete, executable python test case that would check whether the prediction made is true. Format it as a markdown code block with triple backticks including the language name, e.g.
```python
# code here
```
Start every part of the scientific method with its name, e.g.
Hypothesis:
Prediction:
Experiment:
Experiment Results:
Conclusion:

Next, I'm going to provide you with the python code and the surviving mutants generated from it.

{problem}

# Debugging

Hypothesis:
