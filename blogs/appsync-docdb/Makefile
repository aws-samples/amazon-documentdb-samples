all: layer-blog.zip

clean:
		- rm layer-blog.zip

layer-blog.zip:
		mkdir -p nodejs
		npm install mongodb fs
		wget -O ./nodejs/rds-combined-ca-bundle.pem https://s3.amazonaws.com/rds-downloads/rds-combined-ca-bundle.pem
		cp -R  node_modules nodejs/
		cp package.json nodejs/
		zip -r index.zip index.js
		zip -r ./layer-blog nodejs/
