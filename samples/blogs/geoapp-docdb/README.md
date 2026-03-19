# geoapp
Exemplify geospatial query capabilities in Amazon DocumentDB.
The app takes a geospatial coordinate and a distance radius as input. It identifies the US state the coordinate is part of, 
finds the number of airports located in the state and then lists the ones found in the specified radius, sorted by closest.

### Prerequisites
1. Install python requirements
```sh
pip install -r requirements.txt
```

2. Import data set into your Amazon DocumentDB cluster
```sh
unzip dataset/airports_geodata.zip;
mongoimport --ssl --host <DocumentDB-cluster-endpoint> --sslCAFile rds-combined-ca-bundle.pem -u <username> -p <password> -d geodata -c airports dataset/airports-us.json;
  
mongoimport --ssl --host <DocumentDB-cluster-endpoint> --sslCAFile rds-combined-ca-bundle.pem -u <username> -p <password> -d geodata -c states dataset/states-us.json;
```

3. Connect with mongo shell and create 2dsphere index:
```sh
> use geodata
switched to db geodata
> db.airports.createIndex({"loc": "2dsphere"})
```

4. Add the Amazon DocumentDB credentials in AWS Secrets Manager.

### Usage:
Run the script by passing the secret name and the region of the secret.
Enter a geo location (longitude and latitude coordinates) along with the distance radius to look for. 

```sh
usage: geoapp.py [-h] -r REGION -s SECRET

optional arguments:
  -h, --help            show this help message and exit
  -r REGION, --region REGION
                        Specify the region of the secret (e.g. us-east-1)
  -s SECRET, --secret SECRET
                        Specify secret name
```

### Example:

```sh
python3 geoapp.py --region us-east-1 --secret geodata-demo-cluster
Enter your longitude coordinate: -73.9341
Enter your latitude coordinate: 40.8230
Enter distance radius (in km): 40
The geolocation coordinate entered is in the state of: New York
-----------------------------
I have found a number of 29 airports in New York.
-----------------------------
The following airports were found in a 40 km radius:
{'name': 'La Guardia', 'code': 'LGA', 'DistanceKilometers': 7.84283869954285}
{'name': 'Newark Intl', 'code': 'EWR', 'DistanceKilometers': 19.840025284365467}
{'name': 'John F Kennedy Intl', 'code': 'JFK', 'DistanceKilometers': 22.389465314261685}
```

If the geolocation is outside the United States, the script returns an error:

```sh
python3 geoapp.py --region us-east-1 --secret geodata-demo-cluster
Enter your longitude coordinate: -73.895006
Enter your latitude coordinate: 73.895
Enter distance radius (in km): 40
The geo location you entered was not found in the United States!
```
