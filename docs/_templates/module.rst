{{ fullname }}
{% for _ in range(fullname|length) %}={%- endfor %}

.. currentmodule:: {{ fullname }}

.. automodule:: {{ fullname }}
    :members:
    :undoc-members:
    :show-inheritance:
