import h5py
import argparse
import pickle
import numpy as np
from pathlib import Path
from synthesizer.grid import Grid
from utils import (
    get_grid_properties,
    load_grid_params,)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Run a grid of incident cloudy models"
    )

    # path to grid directory (i.e. where incident and new grids are stored)
    parser.add_argument("-incident_grid_dir",
                        type=str,
                        required=True)

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

    # parse arguments
    args = parser.parse_args()
    incident_grid_dir = args.incident_grid_dir
    grid_dir = args.grid_dir
    incident_grid = args.incident_grid
    config_file = args.config_file
    output_dir = args.output_dir

    # define model name
    model_name = f'{incident_grid}-{config_file}'

    # define output directory
    output_directory = f'{output_dir}/{model_name}'

    # load the cloudy parameters you are going to run
    fixed_parameters, photoionisation_axes_values = (
        load_grid_params(config_file))

    # doesn't matter about the ordering of these
    photoionisation_axes = list(photoionisation_axes_values.keys())

    print(photoionisation_axes)

    # open the incident grid using synthesizer
    incident_grid = Grid(
        incident_grid,
        grid_dir=incident_grid_dir,
        read_lines=False,
    )

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
                            verbose=False)

    print('photoionisation_shape', photoionisation_shape)


    # get incident axes
    incident_axes = incident_grid.axes
    incident_axes_values = {axis: getattr(incident_grid, axis)
                            for axis in incident_axes}

    print(incident_axes)
    print(incident_axes_values)

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
                            verbose=False)

    # get axes of the full grid to enable output creation

    print('incident_shape', incident_shape)

    total_axes = incident_axes + photoionisation_axes
    total_axes_values = incident_axes_values | photoionisation_axes_values

    # get properties of the incident grid
    (
        total_n_axes,
        total_shape,
        total_n_models,
        total_mesh,
        total_model_list,
        total_index_list,
    ) = get_grid_properties(total_axes,
                            total_axes_values,
                            verbose=False)

    print('total_shape', total_shape)

    # open the linelist file
    with open(f'{output_directory}/linelist.dat', 'r') as file:
        line_ids = list(map(lambda x: x[:-2], file.readlines()))

    # setup output arrays
    luminosity = {}
    for line_id in line_ids:
        luminosity[line_id] = np.empty(total_shape)

    failed_grid_points = []

    # loop over photoionisation grid points
    for i, photoionisation_index in enumerate(photoionisation_index_list):

        # loop over incident spectra grid points
        for j, incident_index in enumerate(incident_index_list):

            # check to see 
            if not Path(f'{output_directory}/{i+1}/{j}.emergent_elin').is_file():
                print(f'model {i} {j} failed')
                failed_grid_points.append((i, j))



        # # Check to see if pickle file exists. If not append to list of failed
        # # grid points...

        # if not Path(f'{output_directory}/{i}.pck').is_file():
        #     failed_grid_points.append(i)

        #     # ... and also record the line luminosity as False
            
        #     # loop over lines
        #     for line_id in line_ids:

        #         # loop over incident models
        #         for incident_index in incident_index_list:
        #             index = (tuple(list(incident_index) + list(photoionisation_index)))
        #             luminosity[line_id][index] = False


        # # If any models have failed, keep looping but don't bother trying to
        # # read the files.
        # if len(failed_grid_points) == 0:

        #     # Open pickle file
        #     with open(f'{output_directory}/{i}.pck', 'rb') as file:
        #         out = pickle.load(file)

        #         # loop over lines
        #         for line_id in line_ids:

        #             # loop over incident models
        #             for incident_index in incident_index_list:
                        
        #                 # full index
        #                 # print(photoionisation_index, incident_index)

        #                 index = (tuple(list(incident_index)
        #                             + list(photoionisation_index)))
        #                 luminosity[line_id][index] = out[line_id][tuple(incident_index)]

    # # If there are failures list them here:
    # if len(failed_grid_points) > 0:
    #     print(failed_grid_points)

    #     failed_grid_points_string_list = list(map(lambda x: f'{x}\n', failed_grid_points))

    #     # Save this list and generate a new run command
    #     open(f'{model_name}.failed_models', 'w').writelines(failed_grid_points_string_list)

    # open the new grid and save results
    with h5py.File(f"{grid_dir}/{model_name}.hdf5", "w") as hf:

        # save a list of the axes in the correct order
        hf.attrs['axes'] = total_axes

        # save the values of the axes
        for k, v in total_axes_values.items():
            hf[f'axes/{k}'] = v

        for line_id in line_ids:
            hf[f'luminosity/{line_id}'] = luminosity[line_id]

        # print
        hf.visit(print)
