import shutil
import argparse
from pathlib import Path
from synthesizer.grid import Grid
from synthesizer.photoionisation import cloudy23
from utils import (
    get_grid_properties,
    load_grid_params,)


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(
        description="Run a grid of incident cloudy models"
    )

    # path to grid directory (i.e. where incident and new grids are stored)
    parser.add_argument("-grid_dir",
                        type=str,
                        required=True)

    # the name of the incident grid
    parser.add_argument("-incident_grid",
                        type=str,
                        required=True)

    # the cloudy parameters, including any grid axes
    parser.add_argument("-config_file",
                        type=str,
                        required=True)

    # the output directory
    parser.add_argument("-output_dir",
                        type=str,
                        required=True)

    # the path to cloudy
    parser.add_argument("-cloudy_dir",
                        type=str,
                        required=True)

    # the model index
    parser.add_argument("-index",
                        type=str,
                        required=True)

    # parse arguments
    args = parser.parse_args()
    grid_dir = args.grid_dir
    incident_grid = args.incident_grid
    config_file = args.config_file
    cloudy_dir = args.cloudy_dir
    output_dir = args.output_dir
    index = int(args.index)

    # define model name
    model_name = f'{incident_grid}-{config_file}'

    # define output directory
    output_directory = f'{output_dir}/{model_name}'

    # make output directories
    Path(output_directory).mkdir(parents=True, exist_ok=True)

    # for submission system output files
    Path(f"{output_directory}/output").mkdir(parents=True, exist_ok=True)

    # load the cloudy parameters you are going to run
    fixed_parameters, photoionisation_axes_values = (
        load_grid_params(config_file))

    # doesn't matter about the ordering of these
    photoionisation_axes = list(photoionisation_axes_values.keys())
    
    # get properties of the photoionsation grid
    (
        photoionisation_n_axes,
        photoionisation_shape,
        photoionisation_n_models,
        photoionisation_mesh,
        photoionisation_model_list,
        photoionisation_index_list,
    ) = get_grid_properties(photoionisation_axes,
                            photoionisation_axes_values,
                            verbose=True)

    # open the incident grid using synthesizer
    incident_grid = Grid(
        incident_grid,
        grid_dir=grid_dir,
        read_lines=False,
    )

    # get incident axes
    incident_axes = incident_grid.axes
    incident_axes_values = {axis: getattr(incident_grid, axis) for axis in incident_axes}

    print('incident_axes', incident_axes)
    print('incident_axes_values', incident_axes_values)
    print('incident_axes_spectra_shape', incident_grid.spectra['incident'].shape)

    # get properties of the incident grid
    (
        incident_n_axes,
        incident_shape,
        incident_n_models,
        incident_mesh,
        incident_model_list,
        incident_index_list,
    ) = get_grid_properties(incident_axes,
                            incident_axes_values,
                            verbose=True)


    # loop over all incident models

    lam = incident_grid.lam

    for i, (incident_params_tuple, incident_index_tuple) in enumerate(zip(incident_model_list, incident_index_list)):

        lnu = incident_grid.spectra['incident'][incident_index_tuple[0], incident_index_tuple[1]]

        shape_commands = cloudy23.ShapeCommands.table_sed(
            f'{i}',
            lam,
            lnu,
            output_dir=f"{output_directory}")

    # copy linelist
    shutil.copyfile('linelist.dat', f'{output_directory}/linelist.dat')

    print(f'number of cloudy runs per job: {incident_n_models}')
    print(f'number of individual jobs: {photoionisation_n_models}')
    print(f'total number of cloudy runs: {incident_n_models * photoionisation_n_models}')
    print('-'*40)
    print(f'qsub -t 1: {photoionisation_n_models}')