# Inland Consequences

This project aims to create a unified methodology for consequence modeling that seamlessly integrates both coastal and inland approaches, providing adaptable and efficient solutions for a wide range of scenarios.

## Docs Setup

1. Create a Python virtual environment.

```
$ python -m venv venv-inland
$ source ./venv-inland/bin/activate (unix OS) 
$ source ./venv-specs/Scripts/activate (windows OS)
(venv-inland) $
```

2. Install project dependencies.

```
(venv-inland) $ pip install .
```

3. Run the local `mkdocs` server.

```
(venv-inland) $ mkdocs serve
```

### Optional Setup - Markdown Formatting Pre-Commit Hook

To set up a pre-commit hook for [mdformat](https://mdformat.readthedocs.io/en/stable/index.html) to automatically format Markdown files within the repository:

```
(venv-inland) $ pre-commit install
```
