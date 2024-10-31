install:
	pip install --upgrade pip && pip install -r requirements_dev.txt
format:
	isort . --profile black --multi-line 3 && black .
lint:
	pylint main.py src/
test:
	python -m pytest tests/
