#!/bin/bash

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
 
 echo "copy files required to enable secondary reads"
 
 cp ~/operations.go mongo/
 cp ~/mongo.go mongo/
 
 echo  "installing mongobetween"
 go mod tidy
 go clean -modcache
 go install github.com/coinbase/mongobetween
 
 echo "completed script"