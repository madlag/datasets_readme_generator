### How to use

Current directory must be this git root directory.
Just run: ```python main.py```

It will create a READMEs directory, and output a file for each dataset, named X_README.md where X is the dataset name.
(This is temporary, in the end those will have to be named just README.md and moved to the dataset directory)

It creates too a ```error.log``` file with name/exception string for each dataset that failed.   

NB:The script will create a symlink to the datasets subdirectory in your ```datasets``` local install. This is needed by the "test_dataset_common.py" file
