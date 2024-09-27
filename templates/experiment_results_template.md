{% if altexp %}
### {{ name }} Results

### Running {{ name }} on Baseline

{% if not shortexp or not result.debugger_correct %}
{% with result=result.test_correct, name=name.lower(), is_debugger=False, show_exit=True %}
{% include "execution_result_template.md"%}
{% endwith %}
{% endif %}
{% if result.debug_correct %}
{% if not shortexp %}

Debugger Output:

{% endif %}
{% with result=result.debug_correct, name=name.lower(), is_debugger=True %}
{% include "execution_result_template.md"%}
{% endwith %}
{% endif %}

### Running {{ name }} on Mutant

{% if not shortexp or not result.debugger_correct %}
{% with result=result.test_mutant, name=name.lower(), is_debugger=False %}
{% include "execution_result_template.md"%}
{% endwith %}
{% endif %}
{% if result.debug_correct %}
{% if not shortexp %}

Debugger Output:

{% endif %}
{% with result=result.debug_mutant, name=name.lower(), is_debugger=True %}
{% include "execution_result_template.md"%}
{% endwith %}
{% endif %}
{% else %}
### {{ name }} Results

{% if not shortexp or not result.debug %}
{% with result=result.test, name=name.lower(), is_debugger=False, show_exit=True %}
{% include "execution_result_template.md"%}
{% endwith %}
{% endif %}
{% if result.debug %}
{% if not shortexp %}

Debugger Output:

{% endif %}
{% with result=result.debug, name=name.lower(), is_debugger=True %}
{% include "execution_result_template.md"%}
{% endwith %}
{% endif %}
{% endif %}
