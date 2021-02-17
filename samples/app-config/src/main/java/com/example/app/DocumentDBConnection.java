package com.example.app;

import com.mongodb.MongoClientSettings;
import com.mongodb.MongoCredential;
import com.mongodb.ReadPreference;
import com.mongodb.ServerAddress;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoClients;
import com.mongodb.connection.ClusterConnectionMode;
import com.mongodb.connection.ClusterType;
import java.util.Arrays;
import java.util.concurrent.TimeUnit;

public class DocumentDBConnection {

    private static DocumentDBConnection connection;

    private  MongoClient mongoClient = null;

    private DocumentDBConnection()
    {
        this.mongoClient = getMongoClient();
    }

    public static DocumentDBConnection getInstance()
    {
        if (connection ==null)
        {
            connection = new DocumentDBConnection();
        }
        return connection;

    }

    private static MongoClient getMongoClient() {
        configureSSL();
        String username = "<userName>"; //TODO Update user name for DocumentDB
        String password = "<password>"; // TODO Update password for DocumentDB
        String clusterEndpoint = "<clusterEndPoint>";// TODO Update Cluster End Point for DocumentDB

        // Uncomment below for connecting use Connection String
//         String template = "mongodb://%s:%s@%s/test?ssl=false&replicaSet=rs0&readpreference=%s";
//         String readPreference = "secondaryPreferred";
//         String connectionString = String.format(template, username, password, clusterEndpoint, readPreference);
//        MongoClient mongoClient = MongoClients.create(connectionString);

        MongoClientSettings settings =
                MongoClientSettings.builder()
                        .applyToClusterSettings(builder ->
                                builder.hosts(Arrays.asList(new ServerAddress(clusterEndpoint, 27017))))
                        .applyToClusterSettings(builder ->
                                builder.requiredClusterType(ClusterType.REPLICA_SET))
                        .applyToClusterSettings(builder ->
                                builder.requiredReplicaSetName("rs0"))
                        .applyToClusterSettings(builder ->
                                builder.mode(ClusterConnectionMode.MULTIPLE))
                        .readPreference(ReadPreference.secondary())
                        .applyToSslSettings(builder ->
                                builder.enabled(true))
                        .credential(MongoCredential.createCredential(username,"Admin",password.toCharArray()))
                        .applyToConnectionPoolSettings(builder ->
                                builder.maxSize(10))
                        .applyToConnectionPoolSettings(builder ->
                                builder.maxWaitQueueSize(2))
                        .applyToConnectionPoolSettings(builder ->
                                builder.maxConnectionIdleTime(10, TimeUnit.MINUTES))
                        .applyToConnectionPoolSettings(builder ->
                                builder.maxWaitTime(2, TimeUnit.MINUTES))
                        .applyToClusterSettings(builder ->
                                builder.serverSelectionTimeout(30, TimeUnit.SECONDS))
                        .applyToSocketSettings(builder ->
                                builder.connectTimeout(10, TimeUnit.SECONDS))
                        .applyToSocketSettings(builder ->
                                builder.readTimeout(0, TimeUnit.SECONDS))
                        .build();

       MongoClient mongoClient =  MongoClients.create(settings);

        return mongoClient;


    }

    private static void configureSSL() {
        // Update the below variables with your trust store and password
        String truststore = "<truststore>";
        String truststorePassword = "<truststorePassword>";
        System.setProperty("javax.net.ssl.trustStore", truststore);
        System.setProperty("javax.net.ssl.trustStorePassword", truststorePassword);
    }

    public MongoClient getClient()
    {
        return mongoClient;
    }

}
