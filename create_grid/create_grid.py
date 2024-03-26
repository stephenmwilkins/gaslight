import os
import h5py
import argparse
import pickle
import numpy as np
from synthesizer.grid import Grid
from synthesizer.abundances import Abundances
from synthesizer.photoionisation import cloudy23, cloudy17
from utils import (
    get_grid_properties,
    apollo_submission_script,
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

    # get incident axes
    incident_axes = incident_grid.axes
    incident_axes_values = {axis: getattr(incident_grid, axis) for axis in incident_axes}

    print(incident_axes)
    print(incident_axes_values)

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

    print(photoionisation_n_models)

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
                            verbose=False)

    # get axes of the full grid to enable output creation 

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

    print(total_shape)

    # open the first pickle file to get a list of lines
    with open(f'{output_directory}/0.pck', 'rb') as file:
        out = pickle.load(file)
        line_ids = list(out.keys())

    print(line_ids)
    print(type(line_ids))
    print(type(total_axes))

    # setup output arrays
    luminosity = {}
    for line_id in line_ids:
        luminosity[line_id] = np.empty(total_shape)

    for i, index_ in enumerate(photoionisation_index_list):
        # open pickle file
        with open(f'{output_directory}/{i}.pck', 'rb') as file:
            out = pickle.load(file)
            for line_id in line_ids:
                for i in range(out[line_id].shape[0]):
                    for j in range(out[line_id].shape[1]):
                        index = tuple([i, j] + list(index_))
                        luminosity[line_id][index] = out[line_id][i, j]

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
