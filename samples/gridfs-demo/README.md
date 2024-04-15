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
Prior to executing the script, ensure that you have updated the variables in `variables.json` .

### Create text files: 
To create text files of your desired size and number in the `input_file_dest` folder, run:

```
python3 gridfs-demo.py generateFiles
```
### Insert large files into the Amazon DocumentDB: 
To insert the files into the database, run :
```
python3 gridfs-demo.py insertFiles
```
### Retrieve files from Amazon DocumentDB: 
To retrieve files from the database, run:
```
python3 gridfs-demo.py retrieveFiles
```

