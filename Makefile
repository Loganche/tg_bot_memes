# --- env activation ---
#
# source .env/bin/activate
# deactivate

prepare_env:
	python3.10 -m venv .env

prepare_pip:
	python3 -m pip install --upgrade pip
	python3 -m pip install -r requirements.txt

update_requirements:
	python3 -m pip freeze > requirements.txt

prepare_precommit:
	pre-commit install

code_check:
	pre-commit run --all-files
