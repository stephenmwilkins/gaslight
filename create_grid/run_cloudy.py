
import yaml
import os
import shutil
from unyt import eV
import argparse
import pickle
import numpy as np
import h5py
from pathlib import Path
from synthesizer.grid import Grid
from synthesizer.abundances import Abundances
from synthesizer.photoionisation import cloudy23, cloudy17

# local modules
from utils import get_grid_properties, apollo_submission_script


def load_grid_params(param_file="c23.01-test",
                     param_dir="config"):
    """
    Read parameters from a yaml parameter file

    Arguments:
        param_file (str)
            filename of the parameter file
        param_dir (str)
            directory containing the parameter file

    Returns:
        fixed_params (dict)
            dictionary of parameters that are fixed
        grid_params (dict)
            dictionary of parameters that vary on the grid
    """

    # open paramter file
    with open(f"{param_dir}/{param_file}.yaml", "r") as stream:
        try:
            params = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    grid_params = {}
    fixed_params = {}

    # loop over parameters
    for k, v in params.items():

        # if parameter is a list store it in the grid_parameters dictionary
        # and convert to a numpy array
        if isinstance(v, list):
            grid_params[k] = np.array(list(map(float, v)))

        # if a dictionary collect any parameters that are also lists
        elif isinstance(v, dict):
            for k_, v_ in v.items():
                if isinstance(v_, list):
                    grid_params[f'{k}.{k_}'] = np.array(list(map(float, v_)))
                else:
                    fixed_params[f'{k}.{k_}'] = v_

        # otherwise store it in fixed_params dictionary
        else:
            fixed_params[k] = v

    return fixed_params, grid_params


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

    print(photoionisation_axes)

    # set cloudy version
    if fixed_parameters['cloudy_version'] == 'c17.03':
        cloudy = cloudy17
    if fixed_parameters['cloudy_version'] == 'c23.01':
        cloudy = cloudy23

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

    # get properties of the photoionsation grid
    (
        n_axes,
        shape,
        n_models,
        mesh,
        model_list,
        index_list,
    ) = get_grid_properties(photoionisation_axes,
                            photoionisation_axes_values,
                            verbose=True)

    print(n_models)
    print(model_list[index])

    photoionisation_parameters = dict(zip(photoionisation_axes, model_list[index]))
    
    photoionisation_parameters['abundance_scalings'] = {}

    for k, v in photoionisation_parameters.items():
        if len(k.split('.')) > 1:
            if k.split('.')[0] == 'abundance_scalings':
                kk = k.split('.')[1]
                photoionisation_parameters['abundance_scalings'][kk] = v
        
    print(photoionisation_parameters)

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

    print(shape)

    temporary_output_dictionary = None


    # loop over all incident models
    for i, (incident_params_tuple, incident_index_tuple) in enumerate(zip(model_list, index_list)):

        # get a dictionary of all parameters
        incident_parameters = dict(zip(incident_axes, incident_params_tuple))

        # get a dictionary of the parameter grid point
        incident_index = dict(zip(incident_axes, incident_index_tuple))

        # combine parameters
        parameters = (fixed_parameters | incident_parameters
                      | photoionisation_parameters)

        print(i, parameters)

        # create abundance object
        abundances = Abundances(
            metallicity=float(parameters["metallicity"]),
            reference=parameters["reference_abundance"],
            alpha=parameters["alpha"],
            abundances=parameters["abundance_scalings"],
            depletion_model=parameters["depletion_model"],
            depletion_scale=parameters["depletion_scale"],
        )

        # define input SED
        shape_commands = [f'table SED "{i}.sed" \n']

        # Create cloudy input file.
        # This saves each cloudy run with index. These are then read into a
        # master file for each index. linelist.dat is not copied as it should
        # be already copied and throwns an error if it copies it again.
        cloudy.create_cloudy_input(
            index,
            shape_commands,
            abundances,
            output_dir=output_directory,
            copy_linelist=False,
            **parameters,
        )

        input_file = f"{output_directory}/{index}.in"
        cloudy_executable = f'{cloudy_dir}/c23.01/source/cloudy.exe'

        # set CLOUDY_DATA_PATH environment variable
        os.environ['CLOUDY_DATA_PATH'] = f'{cloudy_dir}/c23.01/data/:./'

        os.chdir(output_directory)

        command = f'{cloudy_executable} -r {index}'
        print(command)
        os.system(command)

        # if it's the first index set up the temporary output dictionary
        if not temporary_output_dictionary:

            temporary_output_dictionary = {}

            # read in lines and use line id to set up arrays
            line_ids, wavelengths, luminosities = cloudy23.read_linelist(index)

            for line_id in line_ids:
                temporary_output_dictionary[line_id] = np.empty(shape)

        
        # read in lines and use line id to set up arrays
        line_ids, wavelengths, luminosities = cloudy23.read_linelist(index)

        for line_id, luminosity in zip(line_ids, luminosities):
            temporary_output_dictionary[line_id][incident_index_tuple[0], incident_index_tuple[1]] = luminosity

    print(temporary_output_dictionary[line_id])

    # save the temporary file
    with open(f'{index}.pck', 'wb') as file:
        pickle.dump(temporary_output_dictionary, file)

