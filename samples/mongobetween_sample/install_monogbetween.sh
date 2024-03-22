#!/bin/bash

echo "Disclaimer: This code sample might include components from open-source projects. It is officially not supported by AWS. There's a possibility that future maintenance and updates may not be available."

enableSecondaryReads=0
while getopts "installCustomVersion" opt
do
	case "$opt" in
		a ) enableSecondaryReads=1 ;;
	esac
done

echo "starting steps to install"

sudo yum install golang -y
sudo yum install git -y
export GOPATH="$HOME/go"
PATH="$GOPATH/bin:$PATH"

mkdir -p $GOPATH/src
mkdir -p $GOPATH/bin
mkdir -p $GOPATH/pkg
mkdir -p $GOPATH/src/github.com
mkdir -p $GOPATH/src/github.com/coinbase/

cd $GOPATH/src/github.com/coinbase/
git clone https://github.com/coinbase/mongobetween.git
cd mongobetween/
 
if [ $enableSecondaryReads -eq 1 ]
then
	echo "copy files required to enable secondary reads"
	cp ~/operations.go mongo/ 
	cp ~/mongo.go mongo/
fi
 
echo  "installing mongobetween"
go mod tidy
go clean -modcache
go install github.com/coinbase/mongobetween
 
echo "completed script"
