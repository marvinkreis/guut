### Experiment Results

### Running Experiment on Baseline
{% with result=result.test_correct, name="experiment", is_debugger=False, show_exit=True %}
{% include "execution_result_template.md"%}
{% endwith %}
{% if result.debug_correct %}

Debugger Output:

{% with result=result.debug_correct, name="experiment", is_debugger=True %}
{% include "execution_result_template.md"%}
{% endwith %}
{% endif %}

### Running Experiment on Mutant
{% with result=result.test_mutant, name="experiment", is_debugger=False %}
{% include "execution_result_template.md"%}
{% endwith %}
{% if result.debug_correct %}

Debugger Output:

{% with result=result.debug_mutant, name="experiment", is_debugger=True %}
{% include "execution_result_template.md"%}
{% endwith %}
{% endif %}
{% if (result.test_correct.exitcode == 0) and (result.test_mutant.exitcode == 1) %}

Your experiment resulted in exitcode 0 for the **Baseline** and exitcode 1 for the **Mutant**. This means that your experiment can successfully kill the mutant. Next, you should create a test from your experiment.
{% endif %}
