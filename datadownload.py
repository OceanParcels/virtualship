# # Script/notes to download data from CMEMS

# https://data.marine.copernicus.eu/product/GLOBAL_ANALYSISFORECAST_PHY_001_024/download?dataset=cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i_202211

# 5 to -10 N/S
# -170 to -80 W/E

# All possible depths

# Period?

# files:
# cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i
# cmems_mod_glo_phy-so_anfc_0.083deg_PT6H-i
# cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i
# cmems_mod_glo_phy_anfc_0.083deg_static

# Copy MOTU command from CMEMS website, e.g.
python -m motuclient --motu https://nrt.cmems-du.eu/motu-web/Motu --service-id GLOBAL_ANALYSISFORECAST_PHY_001_024-TDS --product-id cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i --longitude-min -160 --longitude-max -80 --latitude-min -10 --latitude-max 5 --date-min '2023-09-25 00:00:00' --date-max '2023-09-27 00:00:00' --depth-min 0.49402499198913574 --depth-max 5727.9169921875 --variable uo --variable vo --out-dir <OUTPUT_DIRECTORY> --out-name <OUTPUT_FILENAME> --user <USERNAME> --pwd <PASSWORD>

# conda activate cmems  # environment with motuclient==1.8.4 installed

# replace <OUTPUT_DIRECTORY> and <OUTPUT_FILENAME> with your desired output directory and filename
# replace <USERNAME> and <PASSWORD> with your CMEMS credentials (mine are stored in /Users/0448257/Data/copernicus_credentials.txt)
# replace " with ' in the date arguments (doesn't seem to be needed)

python -m motuclient --motu https://nrt.cmems-du.eu/motu-web/Motu --service-id GLOBAL_ANALYSISFORECAST_PHY_001_024-TDS --product-id cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i --longitude-min -170 --longitude-max -75 --latitude-min -10 --latitude-max 5 --date-min '2023-10-10 00:00:00' --date-max '2023-10-12 00:00:00' --depth-min 0.49402499198913574 --depth-max 5727.9169921875 --variable uo --variable vo --out-name studentdata_UV.nc --user edaniels --pwd Pepertj3$
python -m motuclient --motu https://nrt.cmems-du.eu/motu-web/Motu --service-id GLOBAL_ANALYSISFORECAST_PHY_001_024-TDS --product-id cmems_mod_glo_phy-so_anfc_0.083deg_PT6H-i --longitude-min -170 --longitude-max -75 --latitude-min -10 --latitude-max 5 --date-min '2023-10-10 00:00:00' --date-max '2023-10-12 00:00:00' --depth-min 0.49402499198913574 --depth-max 5727.9169921875 --variable so --out-name studentdata_S.nc --user edaniels --pwd Pepertj3$
python -m motuclient --motu https://nrt.cmems-du.eu/motu-web/Motu --service-id GLOBAL_ANALYSISFORECAST_PHY_001_024-TDS --product-id cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i --longitude-min -170 --longitude-max -75 --latitude-min -10 --latitude-max 5 --date-min '2023-10-10 00:00:00' --date-max '2023-10-12 00:00:00' --depth-min 0.49402499198913574 --depth-max 5727.9169921875 --variable thetao --out-name studentdata_T.nc --user edaniels --pwd Pepertj3$

# New files are available! uo, vo, so, thetao all in one file, hourly resolution?
# cmems_mod_glo_phy_anfc_0.083deg_PT1H-m
# test download:
# python -m motuclient --motu https://nrt.cmems-du.eu/motu-web/Motu --service-id GLOBAL_ANALYSISFORECAST_PHY_001_024-TDS --product-id cmems_mod_glo_phy_anfc_0.083deg_PT1H-m --longitude-min -170 --longitude-max -75 --latitude-min -10 --latitude-max 5 --date-min "2023-10-11 23:30:00" --date-max "2023-10-12 23:30:00" --depth-min 0.49402499198913574 --depth-max 5727.9169921875 --variable so --variable thetao --variable uo --variable vo --out-name studentdata11-21.nc --user edaniels --pwd Pepertj3$
# unfortunately only available at the surface, no depth yet...