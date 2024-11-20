import numpy as np
from unyt import Angstrom
from gaslight import exceptions
from synthesizer.units import Quantity
from synthesizer import line_ratios
from synthesizer.line import (
    get_line_id,
    get_line_label,
    get_ratio_label,
    get_diagram_labels,
    get_roman_numeral,
    LineCollection,
)


def get_line_wavelength_from_id(line_id):
    """
    Extracts a wavelength from a line_id

    Arguments:
        line_id (str)
            The cloudy line identification.
    
    Returns:
        wavelength (float)
            The wavelength as a unyt quantity.
    """

    wavelength_string = line_id.split(' ')[-1][:-1]

    if line_id[-1] == 'A':
        unit = Angstrom
    else:
        raise exceptions.UnimplementedFunctionality('units not recognised')
    
    wavelength = float(wavelength_string) * unit

    return wavelength




class Line:
    """
    A class representing a spectral line or set of lines (e.g. a doublet)

    Attributes
    ----------
    lam : wavelength of the line

    Methods
    -------

    """

    wavelength = Quantity()
    luminosity = Quantity()

    def __init__(self, id_, wavelength_, luminosity_):
        self.id_ = id_

        """ these are maintained because we may want to hold on
        to the individual lines of a doublet"""
        self.wavelength_ = wavelength_
        self.luminosity_ = luminosity_

        self.id = get_line_id(id_)

        # mean wavelength of the line in units of AA
        self.wavelength = np.mean(
            wavelength_
        )  

        # total luminosity of the line in units of erg/s/Hz
        self.luminosity = np.sum(
            luminosity_
        )  
       
        # element
        self.element = self.id.split(" ")[0]

    def __str__(self):
        """Function to print a basic summary of the Line object.

        Returns a string containing the id, wavelength, luminosity,
        equivalent width, and flux if generated.

        Returns
        -------
        str
            Summary string containing the total mass formed and
            lists of the available SEDs, lines, and images.
        """

        # Set up string for printing
        pstr = ""

        # Add the content of the summary to the string to be printed
        pstr += "-" * 10 + "\n"
        pstr += f"SUMMARY OF {self.id}" + "\n"
        pstr += f"wavelength: {self.wavelength:.1f}" + "\n"
        pstr += (
            f"log10(luminosity/{self.luminosity.units}): "
            f"{np.log10(self.luminosity):.2f}\n"
        )
        pstr += "-" * 10

        return pstr

    def __add__(self, second_line):
        """
        Function allowing adding of two Line objects together. This should
        NOT be used to add different lines together.

        Returns
        -------
        obj (Line)
            New instance of Line
        """

        if second_line.id == self.id:
            return Line(
                self.id,
                self._wavelength,
                self._luminosity + second_line._luminosity,
            )

        else:
            raise exceptions.InconsistentAddition(
                "Wavelength grids must be identical"
            )
