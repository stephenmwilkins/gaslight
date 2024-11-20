
## Gaslight grid creation

Three steps:

- run `setup_grid_creation.py`, possibly via the helper script `setup_grid_creation.sh`. This extracts the individual incident SEDs and creates machine specific job scripts.

- run the job script created by the previous step. Each job calls `run_cloudy.py` for a particular a photoionisation grid point, looping over the incident grid points.

- run `create_grid.py`, possibly via the helper script `create_grid.sh`. This creates the `gaslight` HDF5 grid.

