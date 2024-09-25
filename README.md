# Virtual_ship_classroom
Emma's work for the MSc student material
Please contact me at e.e.daniels1@uu.nl with any questions.

This is a python tool that will allow students to virtually sample the ocean as if the measurements were coming from an actual oceanographic mission. At the moment we mimic ADCP, CTD, and simple underwaydata measurements and allow surface drifters and argo float deployments. We might add gliders and meteorological data in the future.

### Requirements
To use the material please create an environment called Parcels with the command
`conda env create -f environment.yml

### Input data
The scripts are written to work with A-grid ocean data, specifically that from CMEMS.
Data can be downloaded with the download_data.py script. For now a different conda env is needed for downloading, see comments in the script.

### Sailing the ship
Fill in the accompanying JSON file and run virtualship.py to start measuring. You can also use Sail_the_ship.ipynb

### Ideas for improvements to be made
- ACDP #bins instead of max_depth
- bug when argo(/drifter?) deployed at final location? depth=(len(time))
- documentation that ships sails great circle path
- CTDs op land?
- Argo's/drifters that collide with land. Chance to break?
