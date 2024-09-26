# Quick development

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
environment for each run.

# Setting up a development environment manually

You can set up a development environment by first setting up a virtual environment using:

```bash
python3 -m venv .venv
source ./.venv/bin/activate
```
or
```bash
conda create -n virtual_ship python=3.10
conda activate virtual_ship
```

Then install the dependencies:

```bash
pip install -v -e .[dev]
```

Now you can start with development. Unit tests can be run by typing the command `pytest`, and coverage can be seen by running `pytest --cov=virtual_ship`


# Pre-commit

We use pre-commit to enforce code style and other checks. This can be run by the `nox -s lint` command above, or by installing pre-commit separately and running `pre-commit run --all-files`. If pre-commit is installed separately, you can also install the pre-commit hook into your git repository by running `pre-commit install` such that you don't need to manually run it (it will run when you make a commit).

Either way, the repository is set up to automatically run pre-commit checks and fix errors on every commit, so you should not need to worry about it.
