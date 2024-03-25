
# run a single index

index=1
grid_dir='/research/astrodata/highz/synthesizer/grids'
incident_grid='bpass-2.2.1-bin_chabrier03-0.1,300.0-ages:6.,7.-metallicities:0.0001,0.001,0.01'
config_file='c23.01-test'
output_dir='/its/home/sw376/astrodata/gaslight/cloudy'
cloudy_dir='/research/astro/flare/software/cloudy/'

# run the setup script
python setup_grid_creation.py -grid_dir=$grid_dir -incident_grid=$incident_grid -config_file=$config_file -output_dir=$output_dir -cloudy_dir=$cloudy_dir -index=$index

# now run a single grid point
python run_cloudy.py -grid_dir=$grid_dir -incident_grid=$incident_grid -config_file=$config_file -output_dir=$output_dir -cloudy_dir=$cloudy_dir -index=$index


