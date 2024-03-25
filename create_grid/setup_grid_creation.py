
import yaml
import os
import shutil
from unyt import eV
import argparse
import numpy as np
import h5py
from pathlib import Path
from synthesizer.grid import Grid
from synthesizer.abundances import Abundances
from synthesizer.photoionisation import cloudy23, cloudy17

# local modules
from utils import get_grid_properties, apollo_submission_script



if __name__ == "__main__":
    
    grid_dir = '/Users/sw376/Dropbox/Research/data/synthesizer/grids'
    incident_grid = 'bpass-2.2.1-bin_chabrier03-0.1,300.0-ages:6.,7.-metallicities:0.0001,0.001,0.01'
    config_file = 'c23.01-test'
    cloudy_dir = '/Users/sw376/Dropbox/Research/data/synthesizer/cloudy'
    cloudy_path = '/research/astrodata/highz/synthesizer/cloudy'
    index = 0

    model_name = f'{incident_grid}-{config_file}'
    output_directory = f'{cloudy_dir}/{model_name}'

    # make output directories
    Path(output_directory).mkdir(parents=True, exist_ok=True)

    # for submission system output files
    Path(f"{output_directory}/output").mkdir(parents=True, exist_ok=True)

    # for submission system output files
    Path(f"{output_directory}/seds").mkdir(parents=True, exist_ok=True)

    # open the incident grid using synthesizer
    incident_grid = Grid(
        incident_grid,
        grid_dir=grid_dir,
        read_lines=False,
    )

    # get incident axes
    incident_axes = incident_grid.axes
    incident_axes_values = {axis: getattr(incident_grid, axis) for axis in incident_axes}

    print(incident_axes)
    print(incident_axes_values)

    print(incident_grid.spectra['incident'].shape)

    # get properties of the incident grid
    (
        n_axes,
        shape,
        n_models,
        mesh,
        model_list,
        index_list,
    ) = get_grid_properties(incident_axes,
                            incident_axes_values,
                            verbose=True)


    # loop over all incident models

    lam = incident_grid.lam

    for i, (incident_params_tuple, incident_index_tuple) in enumerate(zip(model_list, index_list)):

        print(i, incident_index_tuple)
        lnu = incident_grid.spectra['incident'][incident_index_tuple[0], incident_index_tuple[1]]

        print(lam.shape, lnu.shape)

        shape_commands = cloudy23.ShapeCommands.table_sed(f'{i}', lam, lnu, output_dir=f"{output_directory}/seds")

