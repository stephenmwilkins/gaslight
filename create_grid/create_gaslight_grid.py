import h5py
from unyt import Angstrom, erg, s, Hz
import argparse
import pickle
import numpy as np
from pathlib import Path
from synthesizer.grid import Grid
from synthesizer.sed import Sed
from synthesizer.abundances import Abundances
from synthesizer.photoionisation import cloudy23, cloudy17
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
    
    # the model index
    parser.add_argument("-normalise",
                        type=str,
                        default=True,
                        required=False)
    
        # the model index
    parser.add_argument("-save_continuum",
                        type=str,
                        default=False,
                        required=False)

    # parse arguments
    args = parser.parse_args()
    incident_grid_dir = args.incident_grid_dir
    grid_dir = args.grid_dir
    incident_grid = args.incident_grid
    config_file = args.config_file
    output_dir = args.output_dir
    normalise = args.normalise
    save_continuum = args.save_continuum

    # define model name
    model_name = f'{incident_grid}-{config_file}'

    # define output directory
    output_directory = f'{output_dir}/{model_name}'

    # load the cloudy parameters you are going to run
    fixed_parameters, photoionisation_axes_values = (
        load_grid_params(config_file))


    # set cloudy version
    if fixed_parameters['cloudy_version'] == 'c17.03':
        cloudy = cloudy17
    if fixed_parameters['cloudy_version'] == 'c23.01':
        cloudy = cloudy23

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
        line_ids = list(map(lambda x: x[:-1], file.readlines()))

    # Setup output arrays.

    # line luminosities and correspinding continuum
    luminosity = {}
    incident_continuum = {}
    nebular_continuum = {}
    transmitted_continuum = {}
    for line_id in line_ids:
        luminosity[line_id] = np.empty(total_shape)
        incident_continuum[line_id] = np.empty(total_shape)
        nebular_continuum[line_id] = np.empty(total_shape)
        transmitted_continuum[line_id] = np.empty(total_shape)

    # continuum
    if save_continuum:

        # read a single cloudy output to get the wavelength grid
        lam = cloudy.read_wavelength(f'{output_directory}/1/0')
        # extend total shape to include wavelength axis
        continuum_total_shape = tuple(total_shape) + lam.shape
        # nebular continuum array
        nebular_continuum_spectra = np.empty(continuum_total_shape)
        # transmission array
        transmission = np.empty(continuum_total_shape)

    failed_grid_points = []

    # Loop over photoionisation grid points.
    for i, photoionisation_index in enumerate(photoionisation_index_list):

        # Loop over incident spectra grid points.
        for j, incident_index in enumerate(incident_index_list):

            # Combine the incident_index and photoionisation_index to get the
            # grid point.
            model_index = tuple(incident_index) + tuple(photoionisation_index)

            # Read synthesizer incident spectra to determine the 
            # normalisation to apply.
            original_lam, original_lnu = np.load(f'{output_directory}/{j}.ssed.npy')
            original_incident_sed = Sed(
                lam=original_lam*Angstrom,
                lnu=original_lnu*erg/s/Hz)

            # read the cloudy output continuum file containing the spectra
            spec_dict = cloudy.read_continuum(
                f'{output_directory}/{i+1}/{j}',
                return_dict=True)

            # create synthesizer Sed object
            cloudy_incident_sed = Sed(
                lam=spec_dict["lam"]*Angstrom,
                lnu=spec_dict["incident"]*erg/s/Hz)

            # calculate normalisation
            normalisation = (cloudy_incident_sed.bolometric_luminosity /
                                original_incident_sed.bolometric_luminosity)

            # check to see if any of the runs failed

            model_file = f'{output_directory}/{i+1}/{j}'

            if ((not Path(f'{model_file}.emergent_elin').is_file())
                or (not Path(f'{model_file}.cont').is_file())):
                print(f'model {i} {j} failed')
                failed_grid_points.append((i, j))

            else:

                # Read in line luminosities and normalise them if required.
                line_ids, line_wavelengths, line_luminosities = cloudy.read_linelist(
                    model_file,
                    extension='emergent_elin')

                if not normalise:
                    normalisation = 1.0

                # record line luminosities and continu
                for line_id, line_luminosity, line_wavelength in zip(
                    line_ids,
                    line_luminosities,
                    line_wavelengths):

                    luminosity[line_id][model_index] = (line_luminosity
                                                               / normalisation)

                    incident_continuum[line_id][model_index] = np.interp(
                        line_wavelength,
                        spec_dict['lam'],
                        spec_dict['incident']
                        ) / normalisation

                    nebular_continuum[line_id][model_index] = np.interp(
                        line_wavelength,
                        spec_dict['lam'],
                        spec_dict['nebular_continuum']
                        ) / normalisation

                    transmitted_continuum[line_id][model_index] = np.interp(
                        line_wavelength,
                        spec_dict['lam'],
                        spec_dict['transmitted']
                        ) / normalisation

                # Save the continuum if requested
                if save_continuum:

                    # check whether the nebular_continuum is the correct length
                    if spec_dict["nebular_continuum"].shape[0] > 0:

                        nebular_continuum_spectra[model_index, :] = (
                            normalisation * spec_dict["nebular_continuum"])

                    # check whether the transmitted and incident are the
                    # correct length
                    if (spec_dict["transmitted"].shape[0] > 0) or (spec_dict["incident"].shape[0] > 0):

                        # transmission is the ratio of the transmitted to
                        # incident spectra.
                        transmission[model_index, :] = (
                            spec_dict["transmitted"] / spec_dict["incident"])

    # If there are failures list them here:
    if len(failed_grid_points) > 0:
        print(failed_grid_points)

        failed_grid_points_string_list = list(map(lambda x: f'{x[0]} {x[1]}\n', failed_grid_points))

        # Save this list and generate a new run command
        open(f'{model_name}.failed_models', 'w').writelines(failed_grid_points_string_list)


    # open the new grid and save results
    with h5py.File(f"{grid_dir}/{model_name}.hdf5", "w") as hf:

        # save a list of the axes in the correct order
        hf.attrs['axes'] = total_axes

        # save the values of the axes
        for k, v in total_axes_values.items():
            hf[f'axes/{k}'] = v

        for line_id, line_wavelength in zip(line_ids, line_wavelengths):
            hf[f'wavelength/{line_id}'] = line_wavelength

        for line_id in line_ids:
            hf[f'luminosity/{line_id}'] = luminosity[line_id]
            hf[f'incident_continuum/{line_id}'] = incident_continuum[line_id]
            hf[f'nebular_continuum/{line_id}'] = nebular_continuum[line_id]
            hf[f'transmitted_continuum/{line_id}'] = transmitted_continuum[line_id]

    # open the new continuum grid and save results
    if save_continuum:
        with h5py.File(f"{grid_dir}/{model_name}-continuum.hdf5", "w") as hf:

            # save a list of the axes in the correct order
            hf.attrs['axes'] = total_axes

            # save the values of the axes
            for k, v in total_axes_values.items():
                hf[f'axes/{k}'] = v

            hf['lam'] = spec_dict['lam']
            hf['nebular_continuum'] = nebular_continuum_spectra
            hf['transmission'] = transmission
