# Dataset Card for "{{dataset_name}}"

## Table of Contents
{% for part, subparts in toc.items() %}- [{{part}}](#{{part|lower|replace(" ", "-")}})
{% for subpart in subparts %}  - [{{subpart}}](#{{subpart|lower|replace(" ", "-")}})
{% endfor %}{% endfor %}


{% for part, subparts in toc.items() %}## [{{part}}](#{{part|lower|replace(" ", "-")}})
{%if part == "Dataset Description" %}
{% for k,v in header.items() %} 
- **{{k}}:** {{v}}{% endfor %}

{% endif %} 

{% for subpart,subpart_content in subparts.items() %}### [{{subpart}}](#{{subpart|lower|replace(" ", "-")}})

{% if subpart == "Data Instances" %} {# ################## DATA INSTANCES #}

{% for config_name, config in configs.items() %} 
{% if configs|length > 1%}
#### {{config_name}}
{% endif %}
An example of '{{config.excerpt_split}}' looks as follows.
```
{{config.excerpt}}
```
{% endfor %} {# end of 'for config_name, config in config.items()' #}

{% elif subpart == "Data Fields" %} {# ################## DATA FIELDS #}
In the following each data field is explained for each config.
 
The data fields are the same among all splits.
{% if subpart_content %}
{{ subpart_content }}
{% else %} 
{% for config_name, config in configs.items() %} 
#### {{config_name}}
{% for field_name, field_description in config.fields.items() %} 
- `{{field_name}}`: {{field_description}}{% endfor %}
{% endfor %} {# end of 'for config_name, config in config.items()' #}
{% endif %}
{% elif subpart == "Data Splits" %} {# ################## DATA SPLIT #}

{% if aggregated_data_splits_str %}
{{aggregated_data_splits_str}}
{% else %}
{% for config_name, config in configs.items() %}
#### {{config_name}}

{{config.data_splits_str}}
{% endfor %}
{% endif %}

{% else %}
{{subpart_content or "[More Information Needed]"}}
{% endif %}

{% endfor %}{% endfor %}

