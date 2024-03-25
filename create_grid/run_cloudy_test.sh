
# run a single index

index=0
grid_dir='/Users/sw376/Dropbox/Research/data/synthesizer/grids'
incident_grid='bpass-2.2.1-bin_chabrier03-0.1,300.0-ages:6.,7.-metallicities:0.0001,0.001,0.01'
config_file='c23.01-test'
output_dir='/Users/sw376/Dropbox/Research/data/synthesizer/cloudy'
cloudy_dir='/Users/sw376/Dropbox/Research/software/cloudy'

python run_cloudy.py -grid_dir=$grid_dir -incident_grid=$incident_grid -config_file=$config_file -output_dir=$output_dir -cloudy_dir=$cloudy_dir -index=$index


