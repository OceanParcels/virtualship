# VirtualShip Quickstart Guide 🚢

Welcome to this Quickstart to using VirtualShip. In this guide we will conduct a virtual expedition in the North Sea. Note, however, that you can plan your own expedition anywhere in the global ocean and conduct whatever measurements you wish!

This guide is intended to give a basic overview of how to plan, initialise and execute a virtual expedition. Data post-processing, analysis and visualisation advice is provided in other sections of the documentation (see [Output](#output) section).

## Cruise planning

> [!NOTE]
> This section describes the custom cruise planning procedure. There is also an option to proceed without your own cruise plan and you can instead use an example route, schedule and selection of measurements (see [Initialise the expedition](#initialise-the-expedition) for more details).

### NIOZ MFP tool

The first step is to plan the expedition. A map and cruise plan can be created through the [NIOZ MFP website](https://nioz.marinefacilitiesplanning.com/cruiselocationplanning#). Documentation on how to use the website can be found [here](https://surfdrive.surf.nl/files/index.php/s/84TFmsAAzcSD56F). Alternatively, you can watch this [video](https://www.youtube.com/watch?v=yIpYX2xCvsM&list=PLE-LzO7kk1gLM74U4PLDh8RywYXmZcloz&ab_channel=VirtualShipClassroom), which runs through how to use the MFP tool.

Below is a screenshot of a North Sea cruise plan we will use in this Quickstart guide. This example cruise departs from Southampton, UK; conduct measurements at one sampling site in the southern North Sea, three in the Dogger Bank region and a further three around the Norwegian Trench before ending in Bergen, Norway.

Feel free to design your expedition as you wish! There is no need to copy these sampling sites in your own expeditions.

![MFP North Sea cruise plan screenshot](image-1.png)

### Export the coordinates

Once you have finalised your MFP cruise plan, select "Export" on the right hand side of the window --> "Export Coordinates" --> "DD". This will download your coordinates as an .xslx (Excel) file, which we will later feed into the VirtualShip protocol to simulate the expedition.

### Instrument selection

You should now consider which measurements are to be taken at each sampling site, and therefore which instruments will be required.

> [!TIP]
> Click [here](assignments/Research_proposal_intro.ipynb) for more information on what measurement options are available, and a brief introduction to each instrument.

To select the instruments for the expedition, open the exported coordinates .xslx file in Excel. Add an extra column called "Instrument" and on each line write which instruments you want to use there. Multiple instrument are allowed, e.g. `DRIFTER, CTD` or `DRIFTER, ARGO_FLOAT, XBT`.

<!-- TODO: this section should be removed/moved to initialisation & scheduling sub-section when the planning UI is implemented. This will remove the need to go into the excel file and instead the workflow will be something like: export .xslx from MFP -> run virtualship init --from-mfp -> launch virtualship plan UI (OR advanced users can simply edit the yamls) -->

## Expedition initialisation & scheduling

VirtualShip is a command line interface (CLI) based tool. From this point on in the Quickstart we will be working predominantly via the command line.

> [!NOTE]
> See [here](https://www.w3schools.com/whatis/whatis_cli.asp) for more information on what a command line interface (CLI) is, if you are unfamiliar.

Now you should navigate to where you would like your expedition to be run on your (virtual) machine (i.e. `cd path/to/expedition/dir/`)

### Initialise the expedition

The next step is to initialise your expedition. Run the following command in your CLI:

```
virtualship init EXPEDITION_NAME --from-mfp CoordinatesExport.xslx
```

> [!TIP] > `CoordinatedExport.xslx` in the `virtualship init` command refers to the .xslx file exported from MFP and edited to include the instrument selection. Replace the filename with the name of your exported .xslx file (and make sure to move it from the Downloads folder/directory to the folder/directory in which you are running the expedition).

This will create a folder/directory called `EXPEDITION_NAME` with two files: `schedule.yaml` and `ship_config.yaml` based on the sampling site coordinates that you specified in your MFP export. The `--from-mfp` flag indictates that the exported coordinates will be used. It will also populate the instrument parameters with the selections made in the edited .xslx file.

> [!NOTE]
> It is also possible to run the expedition initialisation step without an MFP .xslx export file. In this case you should simply run `virtualship init EXPEDITION_NAME` in the CLI. This will write example `schedule.yaml` and `ship_config.yaml` files in the `EXPEDITION_NAME` folder/directory. These files contain example waypoint, timings and instrument selections, but can be edited manually or propagated through the rest of the workflow to run a sample expedition.

### Set the waypoint datetimes

You will need to enter for each of the sampling stations (and the start and end times for the whole expedition). To do this, open the `schedule.yaml` file and replace the `null` fields with datetimes in the format _'YYYY-MM-DD HH:MM:SS'_ (e.g. _'2023-10-20 01:00:00'_).

> [!NOTE]
> It is important to ensure that the timings for each station are realistic. There must be enough time for the ship to travel to each site at a realistic speed (~ 10 knots). The expedition schedule (and the ship's configuration) will be automatically verified later as part of the VirtualShip protocol, but best practice is to ensure that the schedule is feasible at this planning stage.

> [!TIP]
> The MFP planning tool will give estimated durations of sailing between sites, usually at an assumed 10 knots sailing speed. This can be useful to refer back to when planning the expedition timings and entering these into the `schedule.yaml` file.

### Configure the onboard measurements

VirtualShip is capable of taking underway temperature and salinity measurements, as well as onboard ADCP measurements, as the ship sails. To edit their configuration, open `ship_config.yaml`.

Under `adcp_config` provide the configuration of your ADCP, so either `max_depth_meter: -1000.0` if you want to use the OceanObserver or `max_depth_meter: -150.0` if you want to use the SeaSeven (see [here](assignments/Research_proposal_intro.ipynb) for more details on the two ADCP types).

If you don’t need onboard ADCP measurements, remove `adcp_config` and underlying lines from `ship_config.yaml`.

If you do not want to collect temperature and salinity data, remove `ship_underwater_st_config` and underlying lines from `ship_config.yaml`.

> [!NOTE] > **For advanced users only**: you can also edit the CTD, XBT, DRIFTER and ARGO_FLOAT configurations in `ship_config.yaml`. For CTD casts, the measurements will be taken to approximately 20 meters from the ocean floor by default, but this can be changed here if desired.

## Fetch the data

You are now ready to retrieve the input data required for simulating your virtual expedition from the [Copernicus Marine Data Store](https://data.marine.copernicus.eu/products). You will need to register for an account via https://data.marine.copernicus.eu/register.

To retrieve the data, run the following command in your CLI:

```
virtualship fetch EXPEDITION_NAME --username <USERNAME> --password <PASSWORD>
```

Replace `<USERNAME>` and `<PASSWORD>` with your own Copernicus Marine Data Store credentials. Alternatively, you can simply run `virtualship fetch EXPEDITION_NAME` and you will be prompted for your credentials instead.

Waiting for your data download is a great time to practice your level of patience. A skill much needed in oceanographic fieldwork ;-)

## Run the expedition

Once your input data has finished downloading you can run your expedition using the command:

```
virtualship run EXPEDITION_NAME
```

Your command line output should look something like this...

![GIF of example VirtualShip log output](example_log_instruments.gif)

It might take up to an hour to gather the data depending on your choices. Meanwhile read up on some of the [onboard safety procedures](https://virtualship.readthedocs.io/en/latest/user-guide/assignments/Sail_the_ship.html#Emergency-procedures) and browse through [blogs and cruise reports](https://virtualship.readthedocs.io/en/latest/user-guide/assignments/Sail_the_ship.html#Reporting) if you wish.

## Results

Upon successfully completing the simulation, results from the expedition will be stored in the `EXPEDITION_NAME/results` directory, written as .zarr files.

If you are a working on a remote machine, download your results by navigating to `EXPEDITION_NAME/results` and running:

```
zip -r results.zip results/
```

From here you can carry on your analysis offline. We encourage you to explore and analyse these data using [Xarray](https://docs.xarray.dev/en/stable/). We also provide various further [VirtualShip tutorials](https://virtualship.readthedocs.io/en/latest/user-guide/tutorials/index.html) which provide examples of how to visualise data recorded by the VirtualShip instruments.

<!-- TODO: Add a link to visualisation tool as an alternate option to own visualisation when/if this feature is implemented?! -->
