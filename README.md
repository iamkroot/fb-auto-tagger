## Disclaimer
This script has been made for educational purposes **ONLY**. It is illegal to automate interaction with the Facebook website, and the author shall not be held liable for any such actions.

# Autotagger for Facebook

This is a simple python script that enables tagging multiple persons on a comment in Facebook, made using Selenium.

## Features
+ Tag multiple people
+ Ability to exclude those who have already seen the post
+ Fuzzy matching of names

## Limitations
+ Only matches names, so the script cannot differentiate between people with same names

## Running
1. Simply rename the `sample_config.toml` to `config.toml` and edit its contents accordingly.
2. Add the names to `data/names.txt` and `data/exclude.txt`.
3. Optionally, create a separate firefox profile and force disable website notifications in that.
4. Run `pipenv install` to setup the virtualenv.
5. Ensure that the geckodriver is in system `PATH`, it is required by selenium.
5. To start the script, run `pipenv run python auto-tag.py`.
