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


with open('variables.json', 'r') as variables_file:
    vars = json.load(variables_file)

num_files_to_create = vars["num_files_to_create"]
file_size_mb = vars["file_size_mb"]
input_file_dest = vars["input_file_dest"]
filename_prefix = vars["filename_prefix"]

output_folder = vars["output_folder"]

docdb_uri = vars["docdb_uri"]
docdb_dbname = vars["docdb_dbname"]

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

    print(f"Total {filecount} files stored in the database")

def retrive_files():
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

    print("Files retrieved from GridFS and saved to local store successfully in folder: {}".format(output_folder))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='GridFS demo on Amazon DocumentDB')
    parser.add_argument('action', choices=['generateFiles', 'insertFiles', 'retriveFiles'],
                        help='The action to perform: generateFiles, insertFiles, or retriveFiles')
    
    args = parser.parse_args()
    #client = MongoClient('mongodb://' + docdb_username + ':' + docdb_password + '@' + docdb_cluster_endpoint + ':' + docdb_port + '/?replicaSet=rs0&directConnection=true')
    client = MongoClient(docdb_uri)
    if args.action == 'generateFiles':
        generate_textfiles()
    if args.action == 'insertFiles':
        load_large_files_docdb()
    if args.action == 'retriveFiles':
        retrive_files()
