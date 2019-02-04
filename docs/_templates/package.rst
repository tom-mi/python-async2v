{{ fullname }}
{% for _ in range(fullname|length) %}={%- endfor %}

{% if subpackages + submodules %}
.. rubric:: Modules

.. toctree::
   :maxdepth: 5
{% for item in subpackages + submodules %}
   {{ fullname }}.{{ item }}
{%- endfor %}

|

{% endif %}

.. automodule:: {{ fullname }}
