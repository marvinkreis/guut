## Test Instructions

{% if max_experiments_reached %}
You have reached the maximum number of experiments.
{% endif %}
{% if num_turns_left != 0 %}
You have {{ num_turns_left }} {% if not max_experiments_reached %}experiments/{% endif %}tests left.
{% endif %}

Please continue by writing a test that kills the mutant. Remember: the test should pass when executed on the baseline but fail on the mutant.

## Test
