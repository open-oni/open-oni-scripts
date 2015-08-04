#! /bin/bash

# Usage:
# time ./gm_benchmark.sh tif 10

# Parameters:
#   type of file extension to convert FROM (tif, jp2 are current options)
#   number of times it should be converted (optional: default 10)

# Constants
TIMES=10
FILENAME="test"

if [ $# == 0 ]; then
  echo "Whoops!  Please enter a format from which to convert!"
  echo "./gm_benchmark.sh jpg"
elif [ $# -gt 2 ]; then
  echo "Sorry, you entered too many parameters."
  echo "./gm_benchmark.sh jpg 10"
else
  if [ $2 ]; then
    num=$2
  else
    num=$TIMES
  fi
  ext=$1
  file="$FILENAME.$ext"
  # Read in a file
  if [ -e "$file" ]; then
    for ((i=0; i<= num; i++)); do
      echo "$i converting $file"
      gm convert "$file" "$FILENAME.jpg" 
    done
  else
    echo "Unable to find $file in this directory"
  fi
fi