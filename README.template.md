---
---

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
{% if config.download_size %}
Download size: {{ config.download_size }}
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
{{ config.fields }} 
{% endfor %} {# end of 'for config_name, config in config.items()' #}
{% endif %}
{% elif subpart == "Data Splits Sample Size" %} {# ################## DATA SPLITS SIZE #}

{% if aggregated_data_splits_str %}
{{aggregated_data_splits_str}}
{% else %}
{% for config_name, config in configs.items() %}
#### {{config_name}}

{{config.data_splits_str}}
{% endfor %}
{% endif %}

{% else %}
{{subpart_content or MORE_INFORMATION}}
{% endif %}

{% endfor %}{% endfor %}

