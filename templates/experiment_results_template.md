### {{ is_observation and "Observation" or "Experiment" }} Results

#### Script output

```
{{ result.test | format_test_result }}
```
{% if result.test.timeout %}
The experiment was canceled due to a timeout.
{% endif %}
{% if result.test.exitcode != 0 %}
The experiment exited with exit code {{ result.test.exitcode }}.
{% endif %}

{% if result.debug %}
#### Debugger output

```
{{ result.debug | format_debugger_result }}
```
{% endif %}
