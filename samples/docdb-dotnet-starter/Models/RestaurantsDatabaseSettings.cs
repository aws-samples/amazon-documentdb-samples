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
namespace docdb_dotnet_starter.Models
{
    public class RestaurantsDatabaseSettings : IRestaurantsDatabaseSettings
    {
        public string LocationsCollectionName { get; set; }
        public string pathToCAFile { get; set; }
        public string connTemplate { get; set; }
        public string readPreference { get; set; }
        public string DatabaseName { get; set; }
        public string username { get; set; }
        public string password { get; set; }
        public string clusterEndpoint { get; set; }
        public string secretName {get; set; }
        public int defaultPageLength {get;set;}
    }

    public interface IRestaurantsDatabaseSettings
    {
        public string LocationsCollectionName { get; set; }
        public string pathToCAFile { get; set; }
        public string connTemplate { get; set; }
        public string readPreference { get; set; }
        public string DatabaseName { get; set; }
        public string username { get; set; }
        public string password { get; set; }
        public string clusterEndpoint { get; set; }
        public string secretName {get; set; }
        public int defaultPageLength {get;set;}
    }
}