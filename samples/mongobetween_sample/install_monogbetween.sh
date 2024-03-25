#!/bin/bash

echo "Disclaimer: This code sample includes components from open-source projects with some custom code to enable reads from secondary to work with Mongobetween . It is officially not supported by AWS. There is a possibility that future maintenance and updates may not be available.Please choose how you would like to proceed"


options=("Use custom code to enable secondary reads" "Install current main branch from Github" "Quit")
select opt in "${options[@]}"
do
    case $opt in
        "Use custom code to enable secondary reads")
            echo "you chose to use custom code to enable secondary reads"
			enableSecondaryReads=1
			break
            ;;
        "Install current main branch from Github")
            echo "you chose to install current main branch from Github"
			enableSecondaryReads=0
			break
            ;;
        "Quit")
            echo "exiting script"
			exit 1
            ;;
        *) echo "invalid option $REPLY";;
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
