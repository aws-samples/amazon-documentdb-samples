# GridFS Demo 

Sample Python functions to:

-	Generate text files of your desired size and number
-	Insert the files in the specified folder into Amazon DocumentDB using GridFS
-	Retrieve files from Amazon DocumentDB and stored using GridFS in a specified folder.

## Prerequisites
-	Python 3.x
-	Pymongo
  
### AWS Resources:
- An Amazon DocumentDB cluster, see [Creating an Amazon DocumentDB Cluster](https://docs.aws.amazon.com/documentdb/latest/developerguide/db-cluster-create.html)
- Create a [compression enabled collection](https://docs.aws.amazon.com/documentdb/latest/developerguide/doc-compression.html#enabling-compression) for fs.chunks in the database
  
```
db.createCollection( "fs.chunks",{
    storageEngine : {
        documentDB: {
            compression:{
                enable: true
            }
        }
    }
})
```

## Executing gridfs-demo.py

To see all the supported parameters:

```
python3 gridfs-demo.py --help
```

### Create text files: 
To create text files with the default options (5 text files of 32 MB size) in the specified location:

```
python3 gridfs-demo.py --action generateFiles --inputLoc 'files/'
```

To create text files of your desired number, size and prefix in the specified location with:

```
python3 gridfs-demo.py --action generateFiles --numFiles 12 fileSize 48 --filePrefix test --inputLoc files/
```

**Note:** If you specify your prefix, make sure you pass this prefix when you insert files and retrieve files. 

### Insert large files into the Amazon DocumentDB: 

To insert the files into the database with the default file name prefix:

```
python3 gridfs-demo.py --action insertFiles  --inputLoc "files/"  --uri " mongodb://demouser:demopass@demo-docdb.cluster-xxxxx.us-east 1.docdb.amazonaws.com:27017/?replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false"  --db griddb 
```

To insert the files into the database with the specified file prefix:

```
python3 gridfs-demo.py --action insertFiles --filePrefix test  --inputLoc "files/"  --uri " mongodb://demouser:demopass@demo-docdb.cluster-xxxxx.us-east 1.docdb.amazonaws.com:27017/?replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false" --db griddb
```

### Retrieve files from Amazon DocumentDB: 
To retrieve files from the database, with the default file prefix:

```
python3 gridfs-demo.py --action retrieveFiles --outputLoc outfiles/ 
--uri "" mongodb://demouser:demopass@demo-docdb.cluster-xxxxx.us-east 1.docdb.amazonaws.com:27017/?replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false" --db griddb 
```

To retrieve files from the database, with the specified file prefix:

```
python3 gridfs-demo.py --action retrieveFiles --outputLoc outfiles/ --filePrefix test
--uri "" mongodb://demouser:demopass@demo-docdb.cluster-xxxxx.us-east 1.docdb.amazonaws.com:27017/?replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false" --db griddb 
```
