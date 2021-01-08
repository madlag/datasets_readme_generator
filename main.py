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
from collections import defaultdict


def pprint(a):
    print(json.dumps(a, indent=4))

def show_features(features, name="", is_sequence=False):
    if isinstance(features, list):
        return show_features(features[0], name, is_sequence=True)
    if not isinstance(features, dict):
        return []
    if features.get("_type", None) == 'Sequence':
        if "dtype" in features["feature"] or ("_type" in features["feature"] and features["feature"]["_type"] == "ClassLabel"):
            desc = show_features(features["feature"], name, is_sequence=True)
            return desc
        else:
            if is_sequence:
                desc = [f"- `{name}`: a `list` of dictionary features containing:"]
            else:
                desc = [f"- `{name}`: a dictionary feature containing:"]
            for k, v in features["feature"].items():
                pre_desc = show_features(v, name=k)
                desc += ["  " + d for d in pre_desc]
            return desc
    elif features.get("_type", None) == 'Value':
        if is_sequence:
            desc = f"- `{name}`: a `list` of `{features['dtype']}` features."
        else:
            desc = f"- `{name}`: a `{features['dtype']}` feature."
        return [desc]
    elif features.get("_type", None) == 'ClassLabel':
        if is_sequence:
            desc = f"- `{name}`: a `list` of classification labels, with possible values including {', '.join(['`'+nm+'` ('+str(lid)+')' for lid, nm in enumerate(features['names'][:5])])}."
        else:
            desc = f"- `{name}`: a classification label, with possible values including {', '.join(['`'+nm+'` ('+str(lid)+')' for lid, nm in enumerate(features['names'][:5])])}."
        return [desc]
    elif features.get("_type", None) in ['Translation', 'TranslationVariableLanguages']:
        if is_sequence:
            desc = f"- `{name}`: a `list` of multilingual `string` variables, with possible languages including {', '.join(['`'+nm+'`' for nm in features['languages'][:5]])}."
        else:
            desc = f"- `{name}`: a multilingual `string` variable, with possible languages including {', '.join(['`'+nm+'`' for nm in features['languages'][:5]])}."
        return [desc]
    else:
        desc = []
        for k, v in features.items():
            pre_desc = show_features(v, name=k)
            desc += pre_desc
        return desc

class DatasetREADMESingleWriter:
    MORE_INFORMATION = "[More Information Needed](https://github.com/huggingface/datasets/blob/master/CONTRIBUTING.md#how-to-contribute-to-the-dataset-cards)"

    TOC = {
        "Dataset Description": ["Dataset Summary", "Supported Tasks", "Languages"],
        "Dataset Structure": ["Data Instances", "Data Fields", "Data Splits Sample Size"],
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

    def __init__(self, path, name, max_configs=5):
        # Dataset path in datasets repository
        self.path = Path(path)
        # Dataset name
        self.name = name
        # Max number of configs to show
        self.max_configs = max_configs
        # Load the jinja template
        template_file = Path(__file__).parent / "README.template.md"
        self.template = jinja2.Template(template_file.open().read())
        # Initialize the warnings
        self.warnings = []

    def warn(self, message):
        self.warnings.append(message)

    def get_markdown_string(self, markdown_writer):
        # Build a markdown string from a markdown writer (for tables layout for example)
        markdown = ""
        s = StringIO(markdown)
        s.close = lambda: None
        markdown_writer.dump(s)
        f = StringIO(s.getvalue())
        lines = f.readlines()[1:]
        ret = "".join(lines) + "\n\n"
        return ret

    def get_main_config(self):
        if "default" in self.dataset_infos:
            return self.dataset_infos["default"]
        else:
            return list(self.dataset_infos.values())[0]

    def format_size(self, size):
        size = size / 1024 / 1024
        size = "%0.2f MB" % size
        return size

    def get_header(self):
        # Build a dictionary containing information from the dataset for the header part of the jina template
        header_keys = ["Homepage", "Repository", "Paper", "Point of Contact"]

        # Get the main config to get the homepagae information
        main_config = self.get_main_config()
        homepage = main_config["homepage"]

        # Build the dictionary (mostly placeholder right now)
        MORE_INFORMATION = self.MORE_INFORMATION
        download_size = self.global_sizes.get("download_size")
        header_values = [f"[{homepage}]({homepage})", MORE_INFORMATION, MORE_INFORMATION, MORE_INFORMATION]
        if download_size is not None:
            header_keys += ["Download Size"]
            header_values += [self.format_size(download_size)]

        ret = {}
        for i, k in enumerate(header_keys):
            ret[k] = header_values[i]
        return ret

    def ordered_split_names(self, input_config):
        # Try to order the split names, to have something like "train, validation, test"
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
        try:
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
        except:
            self.warn(f"Could not find excerpt for {config_name}/{split_name}")
            return ""

    SIZE_KEYS=["download_size", "dataset_size", "size_in_bytes"]

    def compute_sizes(self):
        self.global_sizes = defaultdict(int)
        for config_name, config in self.dataset_infos.items():
            for key in self.SIZE_KEYS:
                self.global_sizes[key] += config[key]

    def run(self):
        try:
            self.dataset_per_config = self.load_dummy_dataset(self.name)
        except Exception as e:
            self.warn(e)

#        with open(path / (name + ".py")) as f:
#            print(f.read())
#        for filename in os.listdir(self.path):
#            print(filename)

        with open(self.path / "dataset_infos.json") as f:
            self.dataset_infos = json.load(f)
            dataset_infos = self.dataset_infos
            #print(json.dumps(dataset_infos, indent=4))

        self.compute_sizes()

        self.config_names = list(dataset_infos.keys())
        self.config_names.sort()

        self.configs_info = {}
        for config_num, config_name in enumerate(self.config_names[:self.max_configs]):
            input_config = dataset_infos[config_name]
            config = {}
            self.configs_info[config_name] = config

            splits = list(input_config["splits"].keys())
            config["data_splits_str"], config["split_sizes"] = self.config_split_sizes_string(input_config, config_name)

            if "test" in splits and len(splits) != 1:
                splits.remove("test")

            config["excerpt_split"] = random.choice(splits)
            config["excerpt"] = self.get_best_excerpt(config_name, config["excerpt_split"])
            config["fields"] = "\n".join(show_features(input_config["features"]))

            for key in self.SIZE_KEYS:
                if key in input_config:
                    config[key] = self.format_size(input_config[key])

        # Prettyfying the config split size: check if all configs have the same splits, and if yes, build a single
        # table containing all the split sizes
        aggregated_data_splits_str = self.aggregated_config_splits()

        header = self.get_header()

        toc = self.TOC

        for part_name, subparts in toc.items():
            toc[part_name] = {}
            for subpart in subparts:
                toc[part_name][subpart] = self.get_subpart_content(part_name, subpart)

        # Render the template with the gathered information
        ret = self.template.render(
            dataset_name = self.name,
            toc=toc,
            header=header,
            configs=self.configs_info,
            aggregated_data_splits_str=aggregated_data_splits_str,
            MORE_INFORMATION=self.MORE_INFORMATION,
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
        self.errors = {}
        self.warnings = {}

    def dump_info(self, info, kind):
        info_keys = list(info.keys())
        info_keys.sort()
        with open(f"{kind}.log", "w") as info_file:
            for key in info_keys:
                info_file.write(key + ":" + str(info[key]).replace("\n", "    ") + "\n")

    def add_error(self, name, error):
        print("ERROR", error)
        self.errors[name] = str(error)

    def add_warning(self, name, warnings):
        self.warnings[name] = str(warnings)

    def run(self, force=True):
        dest_path = Path(__file__).parent / "datasets"
        if not dest_path.exists():
            dest_path.mkdir()

        p = Path(__file__).parent / "datasets"
        # Create the link to datasets/datasets directory
        if not p.exists():
            datasets_target = Path(datasets.__file__).parent.parent.parent / "datasets"
            p.symlink_to(datasets_target)

        for i, k in enumerate(os.listdir(self.path)):
            try:
                dest_file = dest_path / k  / "README.md"
                if dest_file.exists() and not force :
                    continue
                s = DatasetREADMESingleWriter(self.path / k, k)
                processed = s.run()

                if len(s.warnings) != 0:
                    self.add_warning(k, s.warnings)

                assert(len(processed) != 0)
                with dest_file.open("w") as readme_file:
                    readme_file.write(processed)

            except FileNotFoundError as e:
                if e.filename == None or \
                    e.filename.endswith("dataset_infos.json") or \
                    "dummy_data" in e.filename:
                    self.add_error(k, e)
                else:
                    raise
            except OSError as e:
                if "dummy_data" in str(e):
                    self.add_error(k, e)
                else:
                    raise
            except Exception as e :
                self.add_error(k, e)

        self.dump_info(self.errors, "error")
        self.dump_info(self.warnings, "warning")


def main():
    path = Path("/home/yjernite/Code/kraken_repos/datasets/datasets")
    d = DatasetREADMEWriter(path)
    d.run(force=False)

if __name__ == "__main__":
    main()
