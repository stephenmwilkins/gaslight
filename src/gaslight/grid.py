import h5py
import numpy as np
from unyt import Angstrom, erg, s, Hz, unyt_array, unyt_quantity
import gaslight.exceptions as exceptions
# from gaslight.line import (
#     Line,
#     LineCollection,
#     get_line_wavelength_from_id,
# )

from synthesizer.line import (
    Line,
    LineCollection,
)
from scipy.interpolate import RegularGridInterpolator


class Grid:
    """
    The Grid class, containing attributes and methods for reading and
    manipulating spectral grids.

    Attributes:
        grid_dir (str)
            The directory containing the grid HDF5 file.
        grid_name (str)
            The name of the grid (as defined by the file name)
            with no extension.
        lines (array-like, float)
            The lines array from the grid. This is an N-dimensional grid where
            N is the number of axes of the SPS grid. The final dimension is
            always wavelength.
        parameters (dict)
            A dictionary containing the grid's parameters used in its
            generation.
        axes (list, str)
            A list of the names of the spectral grid axes.
        naxes
            The number of axes the spectral grid has.
        <grid_axis> (array-like, float)
            A Grid will always contain 1D arrays corresponding to the axes
            of the spectral grid. These are read dynamically from the HDF5
            file so can be anything but usually contain at least stellar ages
            and stellar metallicity.
    """

    def __init__(
        self,
        grid_name,
        grid_dir=None,
        lines=None,
    ):
        """
        Initailise the grid object, open the grid file and extracting the
        relevant data.

        Args:
            grid_name (str)
                The file name of the grid (if no extension is provided then
                hdf5 is assumed).
            grid_dir (str)
                The file path to the directory containing the grid file.
            lines (bool)
                Which lines should we read

        """

        # The grid name
        self.grid_name = grid_name

        # The grid directory
        self.grid_dir = grid_dir

        # Construct the full path
        self.grid_filename = (
            f"{self.grid_dir}/{self.grid_name}.hdf5"
        )

        # Get basic info of the grid
        with h5py.File(self.grid_filename, "r") as hf:

            self.parameters = {k: v for k, v in hf.attrs.items()}

            # Get list of axes
            self.axes = list(hf.attrs["axes"])

            # Put the values of each axis in a dictionary
            self.axes_values = {
                axis: hf["axes"][axis][:] for axis in self.axes
            }

            # Set the values of each axis as an attribute
            # e.g. self.log10age == self.axes_values['log10age']
            for axis in self.axes:
                setattr(self, axis, self.axes_values[axis])

            # If no lines are provided read them all
            if not lines:
                lines = list(hf['luminosity'].keys())
            self.lines = lines
            self.line_ids = self.lines
            self.number_of_lines = len(self.line_ids)

            # Get basic details of the grids.
            # number of axes
            self.naxes = len(self.axes)
            self.number_of_axes = self.naxes

            # grid shape
            self.grid_shape = hf["luminosity"][lines[0]][:].shape
            self.nmodels = np.prod(self.grid_shape)

            # get wavelengths from the HDF5 file
            self.wavelength = {line_id: hf[f'wavelength/{line_id}']
                               * Angstrom for line_id in self.line_ids}
            
            # Get line luminosities.
            self.luminosity = {}
            for line_id in self.line_ids:
                self.luminosity[line_id] = hf["luminosity"][line_id][:] * erg / s

            # Get continuum luminosities. These are necessary for calculating
            # equivalent widths.
            self.nebular_continuum = False
            self.incident_continuum = False
            self.transmitted_continuum = False
            self.equivalent_widths = False
            if "nebular_continuum" in hf.keys():
                self.nebular_continuum = {}
                self.transmitted_continuum = {}
                self.incident_continuum = {}
                for line_id in self.line_ids:
                    self.nebular_continuum[line_id] = (
                        hf["nebular_continuum"][line_id][:] * erg / s / Hz)
                    self.incident_continuum[line_id] = (
                        hf["incident_continuum"][line_id][:] * erg / s / Hz)
                    self.transmitted_continuum[line_id] = (
                        hf["transmitted_continuum"][line_id][:] * erg / s / Hz)

        # It is possible that some models may have failed. We can identify
        # these if the value of a H\alpha luminosity is False.
        self.failed_models = (self.luminosity['H 1 6562.80A'].value == False)

        # dictionary holding interpolators
        self.interpolator = {}

        # list of parameters where we interpolate in log space
        self.interpolator_log10 = []

        # create flattened versions of the axes
        self.flatten_axes()

    def __str__(self):
        """
        Function to print a basic summary of the Grid object.
        """

        # Set up the string for printing
        pstr = ""

        # Add the content of the summary to the string to be printed
        pstr += "-" * 30 + "\n"
        pstr += "SUMMARY OF GASLIGHT GRID" + "\n"

        pstr += "Grid dimensions: \n"
        pstr += f"  Numer of axes: {self.naxes}\n"
        pstr += f"  Grid shape: {self.grid_shape}\n"
        pstr += f"  Numer of models: {self.nmodels}\n"
        pstr += f"  Numer of failed models: {np.sum(self.failed_models)} ({100 * np.sum(self.failed_models) / self.nmodels:.2f}%)\n"
        pstr += "Grid axes: \n"
        for axis in self.axes:
            pstr += f"  {axis}: {getattr(self, axis)} \n"

        # pstr += f"available lines: {self.lines}\n"
        pstr += "-" * 30 + "\n"

        return pstr

    def flatten_axes(self):
        """
        Internally called method for creating flattened versions for the axes.
        """

        # flatten the axes
        axes_values_tuple = (self.axes_values[axis] for axis in self.axes)

        axes_values_mesh_tuple = np.meshgrid(*axes_values_tuple, indexing='ij')

        self.axes_values_flattened = {
            axis: axes_values_mesh_tuple[axis_index].flatten()
            for axis_index, axis in enumerate(self.axes)}

        # flatten the list of failed models
        self.failed_models_flattened = self.failed_models.flatten()

    def get_nearest_index(self, value, array):
        """
        Function for calculating the closest index in an array for a
        given value.

        TODO: This could be moved to utils?

        Args:
            value (float/unyt_quantity)
                The target value.

            array (np.ndarray/unyt_array)
                The array to search.

        Returns:
            int
                The index of the closet point in the grid (array)
        """

        # Handle units on both value and array
        # First do we need a conversion?
        if isinstance(array, unyt_array) and isinstance(value, unyt_quantity):
            if array.units != value.units:
                value = value.to(array.units)

        # Get the values
        if isinstance(array, unyt_array):
            array = array.value
        if isinstance(value, unyt_quantity):
            value = value.value

        return (np.abs(array - value)).argmin()

    def get_nearest_grid_point(self, values):
        """
        Function to identify the nearest grid point for a tuple of values.

        Args:
            values (tuple)
                The values for which we want the grid point. These have to be
                in the same order as the axes.

        Returns:
            (tuple)
                A tuple of integers specifying the closest grid point.
        """

        if isinstance(values, list):
            return tuple(
                [
                    self.get_nearest_index(value, getattr(self, axis))
                    for axis, value in zip(self.axes, values)
                ]
            )

        elif isinstance(values, dict):
            return tuple(
                [
                    self.get_nearest_index(values[axis], getattr(self, axis))
                    for axis in self.axes
                ]
            )

    def get_line(
            self,
            line_id,
            covering_fraction=1.0,
            incident_escape_fraction=1.0,
            ):
        """
        Returns the entire grid as a synthesizer.line.Line object.

        Args:
            line_id (str)
                The id of the line.
            covering_fraction (float)
                The covering fraction of ionising photons. This scales the line
                luminosities, nebular and transmitted continuum. The incident
                continuum is scaled by 1 - covering_fraction.
            incident_escape_fraction (float)
                The fraction of the incident (or transmitted) that escapes. 
                This is relevant for modelling e.g. the narrow-line region 
                when the central emitting source is obscured meaning we 
                only see the line emitting region.

        Returns:
            line (synthesizer.line.Line)
                A synthesizer Line object.
        """

        if line_id not in self.line_ids:
            raise exceptions.InconsistentParameter(
                "Provided line_id is" "not in list of available lines."
            )

        wavelength = self.wavelength[line_id]
        luminosity = covering_fraction * self.luminosity[line_id]

        # the transmitted continuum is unaffected by the escape fraction
        continuum = (
            covering_fraction * self.nebular_continuum[line_id] +
            covering_fraction * incident_escape_fraction * self.transmitted_continuum[line_id] +
            (1.0 - covering_fraction) * incident_escape_fraction * self.incident_continuum[line_id])

        # Create and return a synthesizer.lines.Line object
        return Line(line_id, wavelength, luminosity, continuum)

    def get_line_collection(
            self,
            line_ids=None,
            covering_fraction=1.0,
            incident_escape_fraction=1.0,
            ):
        """
        Returns the entire grid as a synthesizer.line.LineCollection object.

        Args:
            line_ids (tuple)
                A tuple of line_ids.
            covering_fraction (float)
                The covering fraction of ionising photons. This scales the line
                luminosities, nebular and transmitted continuum. The incident
                continuum is scaled by 1 - covering_fraction.
            incident_escape (float)
                The fraction of the incident (or transmitted) that escapes. 
                This is relevant for modelling e.g. the narrow-line region 
                when the central emitting source is obscured meaning we 
                only see the line emitting region.


        Returns:
            line_collection (synthesizer.line.LineCollection)
                A synthesizer LineCollection object.
        """
        
        if line_ids is None:
            line_ids = self.lines

        # Line dictionary
        lines = {}

        for line_id in line_ids:
            line = self.get_line(
                line_id,
                covering_fraction=covering_fraction,
                incident_escape_fraction=incident_escape_fraction,
                )

            # Add to dictionary
            lines[line.id] = line

        # Create and return synthesiszer.lines.LineCollection
        return LineCollection(lines)

    def get_line_at_grid_point(
            self,
            grid_point_,
            line_id,
            covering_fraction=1.0,
            incident_escape_fraction=1.0,
            ):
        """
        Function for creating a synthesizer Line object for a given line_id and
        grid_point.

        Args:
            grid_point (tuple or dict)
                A tuple of integers specifying the closest grid point or a
                dictionary containing parameter values.
            line_id (str)
                The id of the line.
            covering_fraction (float)
                The covering fraction of ionising photons. This scales the line
                luminosities, nebular and transmitted continuum. The incident
                continuum is scaled by 1 - covering_fraction.
            incident_escape_fraction (float)
                The fraction of the incident (or transmitted) that escapes. 
                This is relevant for modelling e.g. the narrow-line region 
                when the central emitting source is obscured meaning we 
                only see the line emitting region.


        Returns:
            line (synthesizer.line.Line)
                A synthesizer Line object.
        """

        if isinstance(grid_point_, dict):
            grid_point = self.get_nearest_grid_point(grid_point_)
        if isinstance(grid_point_, tuple):
            grid_point = grid_point_

        # Throw exception if the grid_point has a different shape from the grid
        if len(grid_point) != self.naxes:
            raise exceptions.InconsistentParameter(
                "The grid_point tuple provided"
                "as an argument should have same shape as the grid."
            )

        if line_id not in self.lines:
            raise exceptions.InconsistentParameter(
                "Provided line_id is" "not in list of available lines."
            )

        wavelength = self.wavelength[line_id]
        luminosity = (covering_fraction *
                      self.luminosity[line_id][grid_point])
        # the transmitted continuum is unaffected by the escape fraction
        continuum = (
            covering_fraction * self.nebular_continuum[line_id][grid_point] +
            covering_fraction * incident_escape_fraction * self.transmitted_continuum[line_id][grid_point] +
            (1.0 - covering_fraction) * incident_escape_fraction * self.incident_continuum[line_id][grid_point])

        return Line(line_id, wavelength, luminosity, continuum)

    def get_line_collection_at_grid_point(
            self,
            grid_point_,
            line_ids=None,
            covering_fraction=1.0,
            incident_escape_fraction=1.0
            ):
        """
        Function for creating a Line object for a given line_id and grid_point.

        Args:
            grid_point (tuple)
                A tuple of integers specifying the closest grid point.
            line_id (str)
                The id of the lines to extract. If None use all available 
                lines.
            covering_fraction (float)
                The covering fraction of ionising photons. This scales the line
                luminosities, nebular and transmitted continuum. The incident
                continuum is scaled by 1 - covering_fraction.
            incident_escape_fraction (float)
                The fraction of the incident (or transmitted) that escapes. 
                This is relevant for modelling e.g. the narrow-line region 
                when the central emitting source is obscured meaning we 
                only see the line emitting region.


        Returns:
            line_collection (synthesizer.line.LineCollection)
                A synthesizer LineCollection object.
        """
        
        # Check whether the grid point is a tuple or dictionary
        if isinstance(grid_point_, dict):
            grid_point = self.get_nearest_grid_point(grid_point_)
        if isinstance(grid_point_, tuple):
            grid_point = grid_point_

        if line_ids is None:
            line_ids = self.lines

        # Line dictionary
        lines = {}

        for line_id in line_ids:
            line = self.get_line_at_grid_point(
                grid_point,
                line_id,
                covering_fraction=covering_fraction,
                incident_escape_fraction=incident_escape_fraction,
                )

            # Add to dictionary
            lines[line.id] = line

        # Create and return collection
        line_collection = LineCollection(lines)

        return line_collection

    def setup_interpolator(self, line_ids=None, log10=None):

        """
        Setup the linear interpolator for the lines in line_ids.

        Arguments:
            line_ids (str, list)
                Single line_id or list of line_ids.
            log10 (list)
                List of parameters (axis) to do interpolation in log10 space.
        """

        # if no line_id is provided use all available lines
        if not line_ids:
            line_ids = self.lines

        # if a single line_id is provided turn into a list for iterating
        if isinstance(line_ids, str):
            line_ids = [line_ids]

        self.interpolator_log10 = log10

        # if a parameter is to be interpolated in log10 space
        if log10:
            points = []
            for axis in self.axes:
                if axis in log10:
                    points.append(np.log10(self.axes_values[axis]))
                else:
                    points.append(self.axes_values[axis])
        else:
            points = [self.axes_values[axis] for axis in self.axes]

        for line_id in line_ids:

            values = self.luminosity[line_id]

            self.interpolator[line_id] = RegularGridInterpolator(
                points,
                values)

    def get_interpolated_line(self, parameter_dict, line_id):
        """
        Method for getting the interpolated line luminosity.

        Args:
            parameter_dict (dict)
                A dictionary of parameter values to use.
            line_id (str)
                The id of the line.
            log10 (list)
                List of parameters to interpolate in logspace

        Returns:
            line (synthesizer.line.Line)
                A synthesizer Line object.
        """

        if line_id not in self.interpolator.keys():
            self.setup_interpolator(line_id)

        # create array of parameters in the correct order
        if self.interpolator_log10:
            point = []
            for axis in self.axes:
                if axis in self.interpolator_log10:
                    point.append(np.log10(parameter_dict[axis]))
                else:
                    point.append(parameter_dict[axis])
        else:
            point = [parameter_dict[axis] for axis in self.axes]

        # calculate lumuinisity using interpolation
        luminosity = self.interpolator[line_id](point)

        wavelength = self.wavelength[line_id]

        return Line(line_id, wavelength, luminosity[0])

    def get_interpolated_line_collection(self, parameter_dict, line_ids=None):
        """
        Method for creating a LineCollection using linear interpolation.

        Args:
            parameter_dict (tuple)
                A dictionary of parameters to interpolate.
            line_id (str)
                The id of the line. If None use all available lines.

        Returns:
            line_collection (synthesizer.line.LineCollection)
                A synthesizer LineCollection object.
        """

        if line_ids is None:
            line_ids = self.lines

        # Line dictionary
        lines = {}

        for line_id in line_ids:
            line = self.get_interpolated_line(parameter_dict, line_id)

            # Add to dictionary
            lines[line.id] = line

        # Create and return collection

        line_collection = LineCollection(lines)

        return line_collection
