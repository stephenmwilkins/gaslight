#!/bin/bash
# create a cloudy grid

# path to directory containing grid files
grid_dir="/research/astrodata/highz/synthesizer/grids" 

# path to directory to save cloudy runs
cloudy_dir="/research/astrodata/highz/synthesizer/cloudy"

# machine
machine="apollo"

# path to cloudy execuable
c="/research/astro/flare/software/cloudy/"

cd ..
while IFS="" read -r p || [ -n "$p" ]
do
  arrIN=(${p// / })
  incident=${arrIN[0]}
  params=${arrIN[1]}
  printf '%s\n' "$sps"
  printf '%s\n' "$params"
  echo python3 create_cloudy_input_grid.py -grid_dir $grid_dir -cloudy_dir $cloudy_dir -machine $machine -incident_grid $incident  -cloudy_params $params  -cloudy_path $c
  python3 create_cloudy_input_grid.py -grid_dir $grid_dir -cloudy_dir $cloudy_dir -machine $machine -incident_grid $incident  -cloudy_params $params  -cloudy_path $c
done < synthesizer-grids-apollo_pipeline/create_cloudy_inputs.txt
