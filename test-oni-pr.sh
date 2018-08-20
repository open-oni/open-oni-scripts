#!/bin/bash

function checkBldFile {
	if [ -d "ENV/build" ]; then
		True
	else
		False
	fi
}

function checkPort () {
if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
    echo "Port $1 is running. Please free this port."
    HALTLOAD=True
else
    echo "Port $1 is not running. Ready to roll."
fi
}

BASEDIR="$HOME/development/open-oni/"
BATCHSRCDIR=$BASEDIR"batches"
BATCHDESDIR="$BASEDIR/oo$1/docker/data/"
BATCHDIR="$BATCHDESDIR/batches"
HALTLOAD=False

checkPort 8983
checkPort 3306
checkPort 80
if $HALTLOAD ; then
  exit
fi

cd $BASEDIR
git clone https://github.com/open-oni/open-oni.git oo$1
cd oo$1
git fetch origin
git checkout -b $2 origin/$2
git merge master

rsync -avzh $BATCHSRCDIR $BATCHDESDIR. &
docker-compose up -d
echo "Starting the containers, then waiting for a few seconds to let everything start building."

while [ ! -d "ENV/build" ]; do
	echo "Waiting for Python Packages to start building, please wait..."
	sleep 2
done
while [ -d "ENV/build" ]; do
	echo "Enumerating and building Python Packages (approximately $(ls ./ENV/build 2> /dev/null | wc -l | awk '{print $1}') remaining), please wait... "
	sleep 10
	if ! checkBldFile; then
		echo "  ... seems that the build is done, checking ... "
		sleep 10
	fi
	if ! checkBldFile; then
		echo "  ... seems that the build is done, checking again ... "
		sleep 10
	fi
done
#if [ ! -d "ENV/build" ]; then
#	echo "Waiting for Python Packages to start building, please wait... "
#	sleep 2
#fi
ls -1 $BATCHDIR | grep batch_ |\
   sed '/^\s*$/d' | grep -Ev '^[[:space:]]*$|^#' | sed 's/\s+//g' | tr -d '\r' |\
   xargs -I {} docker-compose exec -T web /load_batch.sh {}
# echo "if you would like to view the logs, 'docker-compose logs'"
