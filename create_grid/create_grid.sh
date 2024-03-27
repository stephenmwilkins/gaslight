
incident_grid_dir='/research/astrodata/highz/synthesizer/grids'
grid_dir='/research/astrodata/highz/gaslight/grids'
incident_grid='bpass-2.2.1-bin_chabrier03-0.1,300.0-ages:6.,7.,8.'
config_file='c23.01-full'
output_dir='/research/astrodata/highz/gaslight/cloudy'

# run the setup script
python create_grid.py -grid_dir=$grid_dir -incident_grid_dir=$incident_grid_dir -incident_grid=$incident_grid -config_file=$config_file -output_dir=$output_dir




