# SURF Resarch Cloud: VirtualShip environment setup

```{note}
This guide is specific to students who are enrolled at Utrecht University.
```

In the class, we will use VirtualShip in the cloud (in this case, SURF Research Cloud - called SURF RC from here-on). This has several advantages:

- You aren't limited to the power of your laptop
- Input datasets are downloaded faster, as they're downloaded to the cloud instance (and not to your laptop)

## 1. Accepting SURF RC invite

In your student email you'll have an invite from SURF Research Access Management (SRAM) to join a project on SURF RC. Accept this invite.

## 2. Open the environment

Navigate to the [SURF Research Cloud Dashboard](https://portal.live.surfresearchcloud.nl/), and click "access" on the shared workspace.

## 3. Jupyter workspace layout and additional config

```{note}
This only needs to be done once during setup.
```

In the Jupyter workspace, you'll see the following in your file explorer:

```
.
├── KERNEL-README.ipynb
├── data
│   └── datasets
|   └── shared-storage    <--- The shared persistent storage
└── scratch
```

The `data/shared-storage` folder is your persistent storage. Here you can make a folder (e.g., `mkdir data/shared-storage/{your-group-name}` replacing `{your-group-name}` with your group name) to house your work for the unit. This folder will be visible to anyone using the workspace, but only you will be able to make edits to it. This is the primary place you should store your `virtualship` configs and content relevant to this unit.

---

To be able to run VirtualShip from the Terminal, we need to take some additional steps which are detailed in the `KERNEL-README.ipynb`. This contains important information for configuring your environment. Namely, for our uses, the "Initialize conda" section. Do the following:

#### Initialize conda

To make the already installed conda-tool available for yourself, you have to initialize your Terminal shell.

Start a "Terminal" tab in the Jupyter Lab launcher and type: `/etc/miniconda/bin/conda init`

Close the Terminal tab and start a new one.
You will see that the Terminal prompt has changed to something like

```
(base) metheuser@mywsp:
```

This is conda telling you that you are currently in the "base" environment.

From here, you already have another environment set up for you. Running `conda env list` in the Terminal, you should see:

```bash
conda env list

# conda environments:
#
base                 * /etc/miniconda
virtualship            /etc/miniconda/envs/virtualship`
```

Here you can do `conda activate virtualship` to activate the environment called "virtualship". This environment is a shared environment among all workspace users that can be centrally updated. If you want, you can create and manage your own environments by running the relevant conda commands.

With the `virtualship` environment, you now have access to the `virtualship` command in your Terminal, which can be confirmed by running `virtualship --help`. From here you can `cd` into `data/shared-storage/{your-name}` and run `virtualship` commands as you would on your local machine.

---

Finally, when you're working in Jupyter Notebooks, you are able to access the Conda environment with `virtualship` and related dependencies by switching the Kernel in the top right of the UI.

## Course facilitator notes

If `virtualship` is updated on GitHub, and you want to update the shared environment, you can do so by running the following commands in the Terminal:

```bash
conda activate virtualship
sudo /etc/miniconda/envs/virtualship/bin/pip install --upgrade git+https://github.com/OceanParcels/virtualship@main
```
