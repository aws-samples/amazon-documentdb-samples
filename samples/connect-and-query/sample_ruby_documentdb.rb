require 'mongo'
require 'neatjson'
require 'json'

client_host = "mongodb://"+ENV['clusterendpoint']
client_options = {
   database: 'sampledb',
   replica_set: 'rs0',
   read: {:secondary_preferred => 1},
   user: ENV['username'],
   password: ENV['password'],
   ssl: true,
   ssl_verify: true,
   ssl_ca_cert: '/home/ubuntu/environment/rds-combined-ca-bundle.pem',
   retry_writes: false
}

data = [{ "_id" => 1, "name" => "Tim", "status"=> "active", "level "=> 12, "score" => 202}, { "_id" => 2, "name" => "Justin", "status" => "inactive", "level" => 2, "score" => 9}, { "_id" => 3, "name" => "Beth", "status" => "active", "level" => 7, "score" => 87}, { "_id" => 4, "name" => "Jesse", "status" => "active", "level" => 3, "score" => 27}]

begin
   ##Create a MongoDB client, open a connection to Amazon DocumentDB as a
   ##   replica set and specify the read preference as secondary preferred
   Mongo::Logger.logger.level = Logger::FATAL
   client = Mongo::Client.new(client_host, client_options)
   ##Insert a single document
   sample = client[:sample]
   x = sample.insert_many(data)
   puts "Successfully inserted data" 
   ##Find the document that was previously written
   result = sample.find(:name => 'Jesse')
   puts "Printing query results"
   #Print the document
   result.each do |document|
      puts JSON.neat_generate(document)
   end
   puts "Updating document"
   result = sample.update_one( { :name => 'Jesse' }, { "$inc" => { :level =>  5 } } )
   puts "Printing updated document"
   result = sample.find(:name => 'Jesse')
   result.each do |document|
      puts JSON.neat_generate(document)
      
   end
   client.close
   client[:sample].drop()
end

#Close the connection
client.close
