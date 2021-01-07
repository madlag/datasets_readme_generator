from pathlib import Path
import os

import random
import json
from pytablewriter import MarkdownTableWriter
from io import StringIO
from pathlib import Path
import jinja2
from utils import pretty_json
import datasets

def pprint(a):
    print(json.dumps(a, indent=4))

class DatasetREADMESingleWriter:
    MORE_INFORMATION = "[More Information Needed]"

    TOC = {
        "Dataset Description": ["Dataset Summary", "Supported Tasks", "Languages"],
        "Dataset Structure": ["Data Instances", "Data Fields", "Data Splits"],
        "Dataset Creation": [
            "Curation Rationale",
            "Source Data",
            "Annotations",
            "Personal and Sensitive Information",
        ],
        "Considerations for Using the Data": [
            "Social Impact of Dataset",
            "Discussion of Biases",
            "Other Known Limitations",
        ],
        "Additional Information": [
            "Dataset Curators",
            "Licensing Information",
            "Citation Information",
        ],
    }

    def __init__(self, path, name):
        self.path = Path(path)
        self.name = name
        # Load the jinja template
        template_file = Path(__file__).parent / "README.template.md"
        self.template = jinja2.Template(template_file.open().read())

    def get_markdown_string(self, markdown_writer):
        markdown = ""
        s = StringIO(markdown)
        s.close = lambda: None
        markdown_writer.dump(s)
        f = StringIO(s.getvalue())
        lines = f.readlines()[1:]
        ret = "".join(lines) + "\n\n"
        return ret

    def get_toc(self):
        return self.TOC

    def get_header(self):
        info = self.dataset_infos
        header_keys = ["Homepage", "Repository", "Paper", "Point of Contact"]

        homepage = None
        for k, v in info.items():
            homepage = v["homepage"]
            break

        MORE_INFORMATION = self.MORE_INFORMATION
        header_values = [homepage, MORE_INFORMATION, MORE_INFORMATION, MORE_INFORMATION]

        ret = {}
        for i, k in enumerate(header_keys):
            ret[k] = header_values[i]

        return ret

    def get_data_fields_description(self):
        output_parts = []
        for config_name, config_info in self.configs_info.items():
            headers = ["field name", "type", "description"]
            values = []
            for field_name, field_description in config_info["fields"].items():
                field_info = self.last_class_info.get(field_name, {})
                try:
                    type = field_info["type"]
                    comment = field_info["comment"]
                except:
                    print("MISSING FIELD INFORMATION", self.dataset_name, config_name, field_name, field_info)
                    raise

                values.append([field_name, type, comment])

            writer = MarkdownTableWriter(
                table_name=f"### {config_name}", headers=headers, value_matrix=values
            )

            output_parts.append(self.get_markdown_string(writer))

        all_the_same = all([output_part == output_parts[0] for output_part in output_parts])
        if all_the_same:
            output = "#### " + ", ".join(list(self.configs_info.keys())) + "\n\n"
            output += output_parts[0]
        else:
            output = ""
            for index, config_name in enumerate(self.configs_info):
                output += f"#### {config_name}\n\n"
                output += output_parts[index]

        return output

    def ordered_split_names(self, input_config):
        split_names = list(input_config["splits"].keys())

        split_names_and_priority = []
        for split_name in split_names:
            if "test" in split_name:
                priority = 2
            elif "valid" in split_name:
                priority = 1
            else:
                priority = 0
            split_names_and_priority.append((priority, split_name))

        split_names_and_priority.sort(key = lambda x : x[0])

        return [e[1] for e in split_names_and_priority]


    def config_split_sizes_string(self, input_config, config_name):
        """Returns the string for the markdown table containing splits size, and a dict containing them."""
        split_names = self.ordered_split_names(input_config)
        headers = [""] + split_names
        values = [[config_name] + [input_config["splits"][key]["num_examples"] for key in split_names]]
        writer = MarkdownTableWriter(
            table_name=f"### {config_name}", headers=headers, value_matrix=values
        )

        data_splits_str = self.get_markdown_string(writer)

        split_sizes = {key: input_config["splits"][key]["num_examples"] for key in split_names}

        return data_splits_str, split_sizes

    def aggregated_config_splits(self):
        """Try to build an aggregated markdown table with sizes for each split for each config, if all configs have the same splits."""
        first_config = list(self.configs_info.keys())[0]
        config_splits0 = list(self.configs_info[first_config]["split_sizes"].keys())

        headers = ["name"] + config_splits0
        values = []

        same_splits = True
        for k, v in self.configs_info.items():
            config_splits = list(v["split_sizes"].keys())
            if config_splits != config_splits0:
                same_splits = False
                break
            values.append([k] + [v["split_sizes"][key] for key in config_splits0])

        if same_splits:
            writer = MarkdownTableWriter(
                table_name="### Configurations", headers=headers, value_matrix=values
            )
            ret = self.get_markdown_string(writer)
            return ret
        else:
            # The splits are not the same -> no aggregated table
            return None

    def get_main_config(self):
        if "default" in self.dataset_infos:
            return self.dataset_infos["default"]
        else:
            return list(self.dataset_infos.values())[0]

    def get_subpart_content(self, part, subpart):
        main_config = self.get_main_config()
        if subpart == "Dataset Summary":
            return main_config.get("description", self.MORE_INFORMATION)
        elif subpart == "Languages":
            return self.MORE_INFORMATION
        elif subpart == "Dataset Curators":
            return self.MORE_INFORMATION
        elif subpart ==  "Licensing Information":
            return main_config["license"] or self.MORE_INFORMATION
        elif subpart == "Citation Information":
            return "```\n" + main_config["citation"] + "\n```"
        elif subpart == "Data Fields":
            return ""
            #return self.get_data_fields_description()

    def load_dummy_dataset(self, dataset_name):
        import test_dataset_common as common
        dataset_tester = common.DatasetTester(None)
        configs = dataset_tester.load_all_configs(dataset_name=dataset_name, is_local=True)
        configs = dataset_tester.check_load_dataset(dataset_name, configs, is_local=True)
        return configs

    def get_best_excerpt(self, config_name, split_name):
        best_excerpt = ""

        MIN_LENGTH = 100
        MAX_LENGTH = 1000
        for i, e in enumerate(self.dataset_per_config[config_name][split_name]):
            if i > 100:
                break
            excerpt = pretty_json(e)
            if len(excerpt) > len(best_excerpt):
                if len(excerpt) < MAX_LENGTH or len(best_excerpt) == 0:
                    best_excerpt = excerpt
            else:
                if len(best_excerpt) > MAX_LENGTH:
                    if len(excerpt) > MIN_LENGTH:
                        best_excerpt = excerpt

        return best_excerpt

    def run(self):
        path = self.path
        name = self.name

        self.dataset_per_config = self.load_dummy_dataset(name)

#        with open(path / (name + ".py")) as f:
#            print(f.read())
#        for filename in os.listdir(self.path):
#            print(filename)

        with open(path / "dataset_infos.json") as f:
            self.dataset_infos = json.load(f)
            dataset_infos = self.dataset_infos
#             (json.dumps(dataset_infos, indent=4))

        self.config_names = list(dataset_infos.keys())
        self.config_names.sort()

        self.configs_info = {}
        for config_name in self.config_names:
            input_config = dataset_infos[config_name]
            config = {}
            self.configs_info[config_name] = config

            config["excerpt_split"] = random.choice(list(input_config["splits"].keys()))
            config["excerpt"] = self.get_best_excerpt(config_name, config["excerpt_split"])
            config["data_splits_str"], config["split_sizes"] = self.config_split_sizes_string(input_config, config_name)

            feature_keys = list(input_config["features"].keys())
            feature_keys.sort()

            def get_feature_string(f):
                if "dtype" in f:
                    return f["dtype"]
                elif "_type" in f:
                    s = ""
                    if "feature" in f:
                        if "dtype" in f["feature"]:
                            s = f["feature"]["dtype"]
                        else:
                            for k, v in f["feature"].items():
                                s += k + ":" + v['dtype'] + ","
                    else:
                        raise Exception("Unknown structure")
                    return f"{f['_type']}[{s}]"

            config["fields"] = {k:get_feature_string(input_config["features"][k]) for k in feature_keys}

        # Prettyfying the config split size: check if all configs have the same splits, and if yes, build a single
        # table containing all the split sizes
        aggregated_data_splits_str = self.aggregated_config_splits()

        header = self.get_header()

        toc = self.get_toc()

        for part_name, subparts in toc.items():
            toc[part_name] = {}
            for subpart in subparts:
                toc[part_name][subpart] = self.get_subpart_content(part_name, subpart)

        # Render the template with the gathered information
        ret = self.template.render(
            dataset_name = name,
            toc=toc,
            header=header,
            configs=self.configs_info,
            aggregated_data_splits_str=aggregated_data_splits_str,
        )

#        yaml_header = self.get_yaml_header() + "\n"
#        ret = yaml_header + ret

        ret = ret.split("\n")
        new_ret = ""
        was_empty = True
        for line in ret:
            empty = len(line.strip()) == 0
            if not empty or not was_empty:
                new_ret += line.rstrip() + "\n"
            was_empty = empty
        ret = new_ret


        return ret


class DatasetREADMEWriter:
    def __init__(self, path):
        self.path = path

    def run(self):
        dest_path = Path(__file__).parent / "READMEs"
        if not dest_path.exists():
            dest_path.mkdir()

        with open("error.log", "w") as errors:
            p = Path(__file__).parent / "datasets"

            # Create the link to datasets/datasets directory
            if not p.exists():
                datasets_target = Path(datasets.__file__).parent.parent.parent / "datasets"
                p.symlink_to(datasets_target)

            for i, k in enumerate(os.listdir(self.path)):
                try:
                    s = DatasetREADMESingleWriter(self.path / k, k)
                    processed = s.run()

                    with (dest_path / (k  + "_README.md")).open("w") as readme_file:
                        readme_file.write(processed)

                except Exception as e :
                    errors.write(k + ":" + str(e) + "\n")

def main():
    path = Path("/home/lagunas/devel/hf/datasets_hf/datasets")
    d = DatasetREADMEWriter(path)
    d.run()

if __name__ == "__main__":
    main()