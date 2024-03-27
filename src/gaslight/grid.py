import h5py
import numpy as np
from unyt import angstrom, unyt_array, unyt_quantity
import gaslight.exceptions as exceptions
from gaslight.line import (
    Line, 
    LineCollection,
    get_line_wavelength_from_id,
)


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

            # Number of axes
            self.naxes = len(self.axes)

            # If no lines are provided read them all

            if not lines:
                lines = list(hf['luminosity'].keys())

            self.wavelengths = {line_id: get_line_wavelength_from_id(line_id)
                                for line_id in lines}
            self.lines = lines

            self.luminosity = {}
            for line in lines:

                # calculate wavelength

                # get luminosity grid
                self.luminosity[line] = hf["luminosity"][line][:]

    def __str__(self):
        """
        Function to print a basic summary of the Grid object.
        """

        # Set up the string for printing
        pstr = ""

        # Add the content of the summary to the string to be printed
        pstr += "-" * 30 + "\n"
        pstr += "SUMMARY OF GASLIGHT GRID" + "\n"
        for axis in self.axes:
            pstr += f"{axis}: {getattr(self, axis)} \n"
        # for k, v in self.parameters.items():
        #     pstr += f"{k}: {v} \n"
        pstr += f"available lines: {self.lines}\n"
    
        pstr += "-" * 30 + "\n"

        return pstr

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

    def get_line(self, grid_point, line_id):
        """
        Function for creating a Line object for a given line_id and grid_point.

        Args:
            grid_point (tuple)
                A tuple of integers specifying the closest grid point.
            line_id (str)
                The id of the line.

        Returns:
            line (synthesizer.line.Line)
                A synthesizer Line object.
        """

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

        luminosity = self.luminosity[line_id][grid_point]
        wavelength = self.wavelengths[line_id]

        return Line(line_id, wavelength, luminosity)

    def get_line_collection(self, grid_point, line_ids=None):
        """
        Function for creating a Line object for a given line_id and grid_point.

        Args:
            grid_point (tuple)
                A tuple of integers specifying the closest grid point.
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
            line = self.get_line(grid_point, line_id)

            # Add to dictionary
            lines[line.id] = line

        # Create and return collection

        line_collection = LineCollection(lines)

        return line_collection
