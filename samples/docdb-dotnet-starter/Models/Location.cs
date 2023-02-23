/*
  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.

  Licensed under the Apache License, Version 2.0 (the "License").
  You may not use this file except in compliance with the License.
  A copy of the License is located at

      http://www.apache.org/licenses/LICENSE-2.0

  or in the "license" file accompanying this file. This file is distributed
  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
  express or implied. See the License for the specific language governing
  permissions and limitations under the License.
*/
using MongoDB.Bson;
using MongoDB.Bson.Serialization.Attributes;

namespace docdb_dotnet_starter.Models
{
    [BsonIgnoreExtraElements]
    public class Location
    {
        [BsonId]
        [BsonRepresentation(BsonType.ObjectId)]
        
        public string Id { get; set; }
        public string URL { get; set; }

        public string name { get; set; }
               
        public string address { get; set; }

        public string address_line_2 { get; set; }

        public string outcode { get; set; }

        public string postcode { get; set; }
                  
        public float rating { get; set; }

        public string type_of_food {get; set;} 

    }
}