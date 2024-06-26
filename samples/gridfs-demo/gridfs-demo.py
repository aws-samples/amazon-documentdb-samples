#  Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License").
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the "license" file accompanying this file. This file is distributed
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
#  express or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from sys import argv
import json
import lorem # type: ignore
import argparse
import os
from datetime import datetime
from pymongo import MongoClient
from gridfs import GridFS


def generate_textfiles():
    
    file_size = file_size_mb * 1024 * 1024
    
    for filno in range(num_files_to_create):
        output_file_name = input_file_dest + filename_prefix+ '_' + str(filno) + '.txt'
        lorem_text = lorem.text()
        repeat_times = file_size // len(lorem_text)
        
        full_content = lorem_text * repeat_times
        with open(output_file_name, 'w') as file:
            file.write(full_content)
            
    print(f"Total {num_files_to_create} text files of size {file_size_mb} MB are generated at '{input_file_dest}' successfully!")


def load_large_files_docdb():
    
    db = client[docdb_dbname]
    fs = GridFS(db)
    filecount = 0

    for file_name in os.listdir(input_file_dest):
        if file_name.startswith(filename_prefix):
            file_path = os.path.join(input_file_dest, file_name)
            file_size_mb = (os.path.getsize(file_path))/(1024*1024)
            start_time =  datetime.now()
            print(f'Starting import of the file {file_path}  with a size of {round(file_size_mb)} MB at: ' + str(start_time))
            
            with open(file_path, 'rb') as file:
                data = file.read()
                fs.put(data, filename=file_name)
                end_time =  datetime.now()
                duration =  end_time - start_time
                print(f'Completed storing the {file_name} in database at ' +  str(end_time) + ', took ' + str(duration) + ' to finish')
                filecount =  filecount + 1

    print(f"Total {filecount} files with {filename_prefix} prefix  stored in the database")

def retrieve_files():
    db = client[docdb_dbname]
    fs = GridFS(db)
    filter_query = {"filename" :{"$regex": f"^{filename_prefix}"}}

    for file in fs.find(filter_query):
        file_name = file.filename
        start_time =  datetime.now()
        print('starting export of file ' +  file_name + ' at time ' + str(start_time))
        output_file_path = os.path.join(output_folder, file_name)

        with open(output_file_path, 'wb') as output_file:
            output_file.write(file.read())
            end_time =  datetime.now()
            duration =  end_time - start_time
        print('completed retrival file in DB at ' +  str(end_time) + ' completed in ' + str(duration))

    print(f"Files with prefix {filename_prefix} retrieved from GridFS and saved to local store successfully in folder: {output_folder}")

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='GridFS demo on Amazon DocumentDB')
    parser.add_argument('--action',required=True, choices=['generateFiles', 'insertFiles', 'retrieveFiles'],
                        help='The action to perform: generateFiles, insertFiles, or retrieveFiles ')
    
    parser.add_argument('--uri', help = 'The URI for Amazon DocumentDB, e.g. mongodb://<insertYourUser>:<insertYourPassword>@<insertYourClusterEndpoint>:<Port>/?replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false')
    parser.add_argument('--db', type=str, help = 'The name of the database that is used to store the files ')

    parser.add_argument('--inputLoc', type=str, help = 'The directory path for the large files to be inserted into the database, and the location where generated files will be stored.')
    parser.add_argument('--numFiles', type=int, default=5, help = '[Optional] Specify the number of text files to be generated in the location set for input file location. If not provided, the default is 5 files')
    parser.add_argument('--fileSize', type=int, default=32, help = '[Optional] Specify the size of each file to be created. If not provided, the default size is 32 MB')
    parser.add_argument('--filePrefix',type=str, default='demotext', help = '[Optional] Specify the prefix that will be used for the generated text files. If not provided, the default is demotext' )
    
    parser.add_argument('--outputLoc', help='The directory path to store the files retrieved from the database ')
    
    args = parser.parse_args()
    
    num_files_to_create = args.numFiles
    file_size_mb = args.fileSize
    input_file_dest = args.inputLoc
    filename_prefix = args.filePrefix
    output_folder = args.outputLoc

    docdb_uri = args.uri
    docdb_dbname= args.db

    client = MongoClient(docdb_uri)
    if args.action == 'generateFiles':
        if input_file_dest is not None: 
            generate_textfiles()
        if input_file_dest is None:
            print(f'Missing option: --inputLoc')
    
    if args.action == 'insertFiles':
        missing_options = []
        if docdb_uri is None:
            missing_options.append('--uri')
        if docdb_dbname is None:
            missing_options.append('--db')
        if input_file_dest is None:
            missing_options.append('--inputLoc')
        if missing_options:
            print(f'Missing options: {", ".join(missing_options)}')
        else:
            load_large_files_docdb()

    if args.action == 'retrieveFiles':
        missing_options = []
        if docdb_uri is None:
            missing_options.append ('--uri')
        if docdb_dbname is None:
            missing_options.append('--db')
        if output_folder is None:
            missing_options.append('--outputLoc')
        if missing_options:
            print(f'Missing options: {", ".join(missing_options)}')
        else:
            retrieve_files()
    
