
# runs the setup script and optionally runs a single grid point

# apollo2
grid_dir='/research/astrodata/highz/synthesizer/grids'
output_dir='/its/home/sw376/astrodata/gaslight/cloudy'
cloudy_dir='/research/astro/flare/software/cloudy/'
machine='apollo2'

# local
# grid_dir='/Users/sw376/Dropbox/Research/data/synthesizer/grids'
# output_dir='/Users/sw376/Dropbox/Research/data/gaslight/cloudy'
# cloudy_dir='/Users/sw376/Dropbox/Research/software/cloudy'

# standard SPS grid
incident_grids=("bpass-2.2.1-bin_chabrier03-0.1,300.0-ages:6.,7.,8.")
config_file=("c23.01-full")

# standard AGN grid
incident_grids=( "agnsed-isotropic" "agnsed-isotropic" )
config_files=( "c23.01-agn-nlr" "c23.01-agn-blr" )

for i in "${!incident_grids[@]}"; do

    incident_grid=${incident_grids[$i]}
    config_file=${config_files[$i]}
    # run the setup script
    python setup_grid_creation.py -grid_dir=$grid_dir -incident_grid=$incident_grid -config_file=$config_file -output_dir=$output_dir -cloudy_dir=$cloudy_dir -machine=$machine

    # now run a single grid point
    # index=1
    # python run_cloudy.py -grid_dir=$grid_dir -incident_grid=$incident_grid -config_file=$config_file -output_dir=$output_dir -cloudy_dir=$cloudy_dir -index=$index

done







