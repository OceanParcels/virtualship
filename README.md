<p align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./docs/_static/virtual_ship_logo_inverted.png">
  <img alt="VirtualShipParcels logo'" width="200" src="./docs/_static/virtual_ship_logo.png">
</picture>
</p>

<!-- Badges -->

---

<!-- SPHINX-START -->
<table>
    <tr>
        <th>Project Owner</th>
        <td>Emma Daniels (e.e.daniels1@uu.nl)</td>
    </tr>
    <tr>
        <!-- Should mirror pyproject.toml. Use one of the "Development status" flags from https://pypi.org/classifiers/-->
        <th>Development status</th>
        <td>Alpha</td>
    </tr>
</table>

<!-- Insert catchy summary -->

VirtualShipParcels is a command line simulator allowing students to plan and conduct a virtual research expedition, receiving measurements as if they were coming from actual oceanographic instruments including:

- ADCP (for currents)
- CTD (for conductivity, and temperature)
- underwater measurements (salinity and temperature)
- surface drifters
- argo float deployments

<!-- TODO: future. Along the way students will encounter difficulties such as: -->

## Installation

For a normal installation do:

```bash
conda create -n my_env python=3.12
conda activate my_env
conda install -c conda-forge virtualship
```

For a development installation, please follow the instructions detailed in the [contributing page](.github/CONTRIBUTING.md).

## Usage

Copy the expedition directory, and fill in the accompanying YAML file. Then run `virtualship run <dir>` to start measuring.

<!-- TODO: once virtualship cli endpoint is done, just copy paste `virtualship --help` output here. -->

## Input data

The scripts are written to work with A-grid ocean data from CMEMS.
