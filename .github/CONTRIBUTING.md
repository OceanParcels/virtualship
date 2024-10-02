# Contributing

## Quick development

The fastest way to start with development is to use nox. If you don't have nox,
you can use `pipx run nox` to run it without installing, or `pipx install nox`.
If you don't have pipx (pip for applications), then you can install with
`pip install pipx` (the only case were installing an application with regular
pip is reasonable). If you use macOS, then pipx and nox are both in brew, use
`brew install pipx nox`.

To use, run `nox`. This will lint and test using every installed version of
Python on your system, skipping ones that are not installed. You can also run
specific jobs:

```console
$ nox -s lint   # Lint only
$ nox -s tests  # Python tests
$ nox -s docs   # Build and serve the documentation
$ nox -s build  # Make an SDist and wheel
```

Nox handles everything for you, including setting up an temporary virtual
environment for each run. Run `nox --list` to see all available jobs. The docs environment is re-used between runs, so if adding new dependencies, you may need to run `nox -s docs --reuse-venv=no` to ensure the environment is up to date.

## Setting up a development environment manually

You can set up a development environment by first setting up a virtual environment using:

```bash
python3 -m venv .venv
source ./.venv/bin/activate
```

or

```bash
conda create -n ship python=3.10
conda activate ship
```

Then install the dependencies:

```bash
pip install -v -e ".[dev]"
```

Now you can start with development. Unit tests can be run by typing the command `pytest`, and coverage can be seen by running `pytest --cov=virtualship`

---

For documentation, we use a conda environment. Due to limitations with `nox` being unable to read YAML files, we use a `conda_requirements.txt` file instead.

```bash
conda create -n ship-docs python=3.10
conda activate ship-docs
conda install --file docs/conda_requirements.txt
```

## Pre-commit

We use pre-commit to enforce code style and other checks. This can be run by the `nox -s lint` command above, or by installing pre-commit separately and running `pre-commit run --all-files`. If pre-commit is installed separately, you can also install the pre-commit hook into your git repository by running `pre-commit install` such that you don't need to manually run it (it will run when you make a commit).

Either way, the repository is set up to automatically run pre-commit checks and fix errors on every commit, so you should not need to worry about it.

---

---

## For maintainers

### Release checklist

- Go to GitHub, draft new release. Enter name of version and "create new tag" if it doesn't already exist. Click "Generate Release Notes". Currate release notes as needed. Look at a previous version release to match the format (title, header, section organisation etc.)
- Go to [conda-forge/virtualship-feedstock](https://github.com/conda-forge/virtualship-feedstock), create a new issue (select the "Bot Commands" issue from the menu) with title `@conda-forge-admin, please update version`. This will prompt a build, otherwise there can be a delay in the build.
  - Approve PR and merge on green
- Check "publish to PyPI" workflow succeeded
