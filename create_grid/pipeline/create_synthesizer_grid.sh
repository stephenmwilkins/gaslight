#!/bin/bash

# path to directory containing grid files
grid_dir="/research/astrodata/highz/synthesizer/grids" 

# path to directory to save cloudy runs
cloudy_dir="/research/astrodata/highz/synthesizer/cloudy"

# machine
machine="apollo"


# cd ..
# while IFS="" read -r p || [ -n "$p" ]
# do
#   arrIN=(${p// / })
#   grid=${arrIN[0]}
#   echo $grid
#   python3 create_synthesizer_grid.py -grid_name $grid -grid_dir $grid_dir -cloudy_dir $cloudy_dir -machine $machine -line_calc_method linelist
# done < synthesizer-grids-apollo_pipeline/grids.txt


cd ..
while IFS="" read -r p || [ -n "$p" ]
do
  arrIN=(${p// / })
  incident=${arrIN[0]}
  params=${arrIN[1]}
  printf '%s\n' "$sps"
  printf '%s\n' "$params"
  python create_synthesizer_grid.py -grid_dir $grid_dir -cloudy_dir $cloudy_dir -machine $machine -incident_grid $incident -cloudy_params $params
done < synthesizer-grids-apollo_pipeline/create_synthesizer_grid.txt
