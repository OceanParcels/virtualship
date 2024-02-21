# Virtual_ship_classroom
Emma's work for the MSc student material
Please contact me at e.e.daniels1@uu.nl with any questions. 

This is a python tool that will allow students to virtually sample the ocean as if the measurements were coming from an actual oceanographic mission. At the moment we mimic ADCP, CTD, and simple underwaydata measurements and allow surface drifters and argo float deployments. We might add gliders and meteorological data in the future. 

### Requirements
To use the material please create an environment called Parcels with the command
`conda env create -f environment.yml

### Input data
The scripts are written to work with A-grid ocean data, specifically that from CMEMS
Sample instructions for data to be downloaded can be found in 
`datadownload.py` 

### Sailing the ship
Fill in the accompanying JSON file and run virtualship.py to start measuring. 