
"""
Simple script to create a grid containing a limited set of lines, for example
only those needed for one particular diagram or set of diagrams.
"""


from gaslight.grid import Grid
import h5py
from synthesizer.line import (
    flatten_linelist,)
from synthesizer import line_ratios

# define the diagram of interest
diagram_id = 'BPT-NII'

grid_dir = '/Users/sw376/Dropbox/Research/data/gaslight/grids'
grid_name = 'bpass-2.2.1-bin_chabrier03-0.1,300.0-ages:6.,7.,8.-c23.01-full'

old_grid_filename = f'{grid_dir}/{grid_name}.hdf5'
new_grid_filename = f'{grid_dir}/{grid_name}-{diagram_id}.hdf5'


# get the relevant ratio definition
diagram_lines = line_ratios.diagrams[diagram_id]

print(diagram_lines)

lines = []

for l in diagram_lines:
    if isinstance(l, list):
        for l_ in l:
            if isinstance(l_, list):
                for l__ in l_:
                    lines.append(l__)
            elif isinstance(l_, 'str'):
                lines.append(l_)
    elif isinstance(l, 'str'):
        lines.append(l)


lines = list(set(lines))


with h5py.File(old_grid_filename, 'r') as old_grid:

    # hf.visit(print)
    print(list(old_grid.attrs))
    axes = old_grid.attrs['axes']

    with h5py.File(new_grid_filename, 'w') as new_grid:

        for k, v in old_grid.attrs.items():
            new_grid.attrs[k] = v

        for axis in axes:
            new_grid[f'axes/{axis}'] = old_grid[f'axes/{axis}'][:]

        for line in lines:
            new_grid[f'luminosity/{line}'] = old_grid[f'luminosity/{line}'][:]

