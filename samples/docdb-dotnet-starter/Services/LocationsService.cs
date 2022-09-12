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

using System;
using System.Text;
using docdb_dotnet_starter.Models;
using MongoDB.Driver;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Amazon.SecretsManager;
using Amazon.SecretsManager.Extensions.Caching;

namespace docdb_dotnet_starter.Services
{
    public class LocationsService
    {
        private readonly IMongoCollection<Location> _locations;
        private SecretsManagerCache cache = new SecretsManagerCache();
        private int pageLength = 100;

        public LocationsService(IRestaurantsDatabaseSettings settings)
        {
            this.pageLength = settings.defaultPageLength;
            string  docdbSecret = settings.secretName;
            //System.Console.WriteLine("docdbSecret");
            var secret = this.GetDocDBSecret(docdbSecret);
            secret.Wait();

            string connectionString = String.Format(settings.connTemplate, secret.Result.user, secret.Result.pass, 
                                                    settings.clusterEndpoint, settings.clusterEndpoint, settings.readPreference);
            var settings1 = MongoClientSettings.FromUrl(new MongoUrl(connectionString));
            var client = new MongoClient(settings1);
            var database = client.GetDatabase(settings.DatabaseName);
            _locations = database.GetCollection<Location>(settings.LocationsCollectionName);
        }

        public async Task<(string user, string pass)> GetDocDBSecret(string secretId)
        {
            var sec = await this.cache.GetSecretString(secretId);
            var output = Newtonsoft.Json.Linq.JObject.Parse(sec);
            //Console.WriteLine(output);
            return ( user: output["username"].ToString(), pass: output["password"].ToString());
        }

        public List<Location> Get(int pageLength)
        {                        
            return _locations.Find(location => true).Limit(pageLength == 0 ? this.pageLength: pageLength).ToList();        
        } 

        public Location Get(string id) => _locations.Find(location => location.Id == id).FirstOrDefault();

        public Location Create(Location location)
        {
            _locations.InsertOne(location);

            return location;
        }

        public void Update(string id, Location updatedLocation) => _locations.ReplaceOne(location => location.Id == id, updatedLocation);

        public void Delete(Location locationForDeletion) => _locations.DeleteOne(location => location.Id == locationForDeletion.Id);

        public void Delete(string id) => _locations.DeleteOne(location => location.Id == id);
    }
}