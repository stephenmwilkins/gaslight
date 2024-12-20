import numpy as np
import yaml


def get_grid_properties(axes, axes_values, verbose=False):
    """
    Get the properties of the grid including the dimensions etc.
    """

    # the grid axes
    if verbose:
        print(f"axes: {axes}")

    # number of axes
    n_axes = len(axes)
    if verbose:
        print(f"number of axes: {n_axes}")

    # the shape of the grid (useful for creating outputs)
    shape = list([len(axes_values[axis]) for axis in axes])
    if verbose:
        print(f"shape: {shape}")

    # determine number of models
    n_models = np.prod(shape)
    if verbose:
        print(f"number of models to run: {n_models}")

    # create the mesh of the grid
    mesh = np.array(
        np.meshgrid(*[np.array(axes_values[axis]) for axis in axes])
    )

    # create the list of the models
    model_list = mesh.T.reshape(n_models, n_axes)
    if verbose:
        print("model list:")
        print(model_list)

    # create a list of the indices

    index_mesh = np.array(np.meshgrid(*[range(n) for n in shape]))

    index_list = index_mesh.T.reshape(n_models, n_axes)
    if verbose:
        print("index list:")
        print(index_list)

    return n_axes, shape, n_models, mesh, model_list, index_list


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


def apollo2_submission_script(grid_dir,
                             output_dir,
                             cloudy_dir,
                             incident_grid,
                             config_file):
    """
    Create an Apollo SGE submission script.

    Arguments:

    Returns:
        None
    """

    apollo_job_script = f"""
######################################################################
# Options for the batch system
# These options are not executed by the script, but are instead read by the
# batch system before submitting the job. Each option is preceeded by '#$' to
# signify that it is for grid engine.
#
# All of these options are the same as flags you can pass to qsub on the
# command line and can be **overriden** on the command line. see man qsub for
# all the details
######################################################################
# -- The shell used to interpret this script
#$ -S /bin/bash
# -- Execute this job from the current working directory.
#$ -cwd
#$ -l h_vmem=4G
#$ -l m_mem_free=4G
# -- Job output to stderr will be merged into standard out. Remove this line if
# -- you want to have separate stderr and stdout log files
#$ -j y
#$ -o output/
# -- Send email when the job exits, is aborted or suspended
# #$ -m eas
# #$ -M YOUR_USERNAME@sussex.ac.uk
######################################################################
# Job Script
# Here we are writing in bash (as we set bash as our shell above). In here you
# should set up the environment for your program, copy around any data that
# needs to be copied, and then execute the program
######################################################################

grid_dir='{grid_dir}'
output_dir='{output_dir}'
cloudy_dir='{cloudy_dir}'
incident_grid='{incident_grid}'
config_file='{config_file}'

source ../venv/bin/activate
python run_cloudy.py -grid_dir=$grid_dir -incident_grid=$incident_grid -config_file=$config_file -output_dir=$output_dir -cloudy_dir=$cloudy_dir -index=$SGE_TASK_ID

"""

    # save job script
    open(f"{incident_grid}-{config_file}.job", "w").write(apollo_job_script)

