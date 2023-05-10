PYTHON=python3

clean:
	- rm -rf .aws-sam/*

build:  template.yaml
	sam build

sam: build
	sam deploy --capabilities CAPABILITY_NAMED_IAM --guided
