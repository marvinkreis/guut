### Experiment Results

### Running Experiment on Baseline
```
{{ result.test_correct | format_test_result }}
```
{% if result.test_correct.timeout %}
Your code resulted in a timeout (5s) and exited with exit code {{ result.test_correct.exitcode }}.
{% elif result.test_correct.exitcode != 0 %}
Your code exited with exit code {{ result.test_correct.exitcode }}.
{% endif %}
{% if result.debug_correct %}

Debugger Output:
```
{{ result.debug_correct | format_debugger_result }}
```
{% endif %}

### Running Experiment on Mutant
```
{{ result.test_mutant | format_test_result }}
```
{% if result.test_mutant.timeout %}
Your code resulted in a timeout (5s) and exited with exit code {{ result.test_mutant.exitcode }}.
{% elif result.test_mutant.exitcode != 0 %}
Your code exited with exit code {{ result.test_mutant.exitcode }}.
{% endif %}
{% if result.debug_mutant %}

Debugger Output:
```
{{ result.debug_mutant | format_debugger_result }}
```
{% endif %}
{% if (result.test_correct.exitcode == 0) and (result.test_mutant.exitcode == 1) %}

Your experiment resulted in exitcode 0 for the **Baseline** and exitcode 1 for the **Mutant**. This means that your experiment can successfully kill the mutant. Next, you should write a conclusion and create a test from your experiment.
{% endif %}
