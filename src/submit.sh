#!/bin/bash -l
#
#SBATCH -J VSC              # the name of your job   
#SBATCH -p short            # request the short partition, job takes less than 3 hours  
#SBATCH -t 3:00:00          # time in hh:mm:ss you want to reserve for the job
#SBATCH -n 1                # the number of cores you want to use for the job, SLURM automatically determines how many nodes are needed
#SBATCH -o log%j.o        # the name of the file where the standard output will be written to. %j will be the jobid determined by SLURM
#SBATCH -e log%j.e        # the name of the file where potential errors will be written to. %j will be the jobid determined by SLURM

conda activate parcels
srun ./cruise_simulation.py           
