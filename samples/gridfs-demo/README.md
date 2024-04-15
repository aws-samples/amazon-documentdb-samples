# GridFS Demo 

Sample Python functions to:

-	Generate text files of your desired size and number
-	Insert the files in the specified folder into Amazon DocumentDB using GridFS
-	Retrieve files from Amazon DocumentDB and stored using GridFS in a specified folder.

## Prerequisites
-	Python 3.x
-	Pymongo
### AWS Resources:
•	An Amazon DocumentDB cluster, see Creating an Amazon DocumentDB Cluster
•	Create a compression enabled collection for fs.chunks in the database
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
Prior to executing the script, ensure that you have updated the variables in ```variables.json``` to set up the script.
### Create text files: 
Creation of text files is optional, if you have files to insert into the database using Gridfs, you can place all files in a folder and set the input_file_dest to that folder.
```
python3 gridfs-demo.py generateFiles
```
### Insert large files into the Amazon DocumentDB: 
To insert the files into the database, run :
```
python3 gridfs-demo.py insertFiles
```
### Retrive files from Amazon DocumentDB: 
To retrieve files from the database, run:
```
python3 gridfs-demo.py retriveFiles
```

