package com.example.app;

import com.github.javafaker.Faker;
import com.mongodb.MongoSocketOpenException;
import com.mongodb.MongoSocketReadException;
import com.mongodb.client.MongoClient;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoCursor;
import com.mongodb.client.MongoDatabase;
import com.mongodb.client.model.InsertManyOptions;
import org.bson.Document;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;


public class DocumentDBClient {

    public static void main(String[] args) throws InterruptedException {


        // get client object using Singleton pattern
        MongoClient mongoClient = DocumentDBConnection.getInstance().getClient();

        // get database to use
        MongoDatabase database = mongoClient.getDatabase("documentDB");

        // get to collection from database
        MongoCollection<Document> collection = database.getCollection("test");

        // create data
        demoRetryWrites(collection);

        Document document = new Document();
        document.put("firstName", "James");
        document.put("age", 44);
        collection.insertOne(document);

        // bulk insert
        List<Document> documentList = getDocumentsForBulkWrite();
        collection.insertMany(documentList, new InsertManyOptions().ordered(false));

        // update data
        Document query = new Document();
        query.put("firstName", "James");
        Document newDocument = new Document();
        newDocument.put("firstName", "Jane");
        Document updateObject = new Document();
        updateObject.put("$set", newDocument);
        collection.updateOne(query, updateObject);

        // read data
        Document searchQuery = new Document();
        searchQuery.put("firstName", "Jane");
        MongoCursor<Document> cursor = collection.find(searchQuery).iterator();

        try {
            while (cursor.hasNext()) {
                System.out.println(cursor.next());
            }
        } finally {
            cursor.close();
        }

        // delete data
        Document deleteQuery = new Document();
        deleteQuery.put("firstName", "Jane");
        collection.deleteOne(deleteQuery);
    }

    private static void demoRetryWrites(MongoCollection<Document> collection) {
        final int[] FIBONACCI = new int[]{2, 3, 5};
        final List<Class<? extends Exception>> possibleErrorList = new ArrayList<Class<? extends Exception>>();
        possibleErrorList.add(MongoSocketOpenException.class);
        possibleErrorList.add(MongoSocketReadException.class);
        for (int attempt = 0; attempt < FIBONACCI.length; attempt++) {
            try {
                performWriteOperation(collection);
                return;
            } catch (Exception e) {
                if (!possibleErrorList.contains(e.getClass()))
                    throw new RuntimeException(e);
                try {
                    Thread.sleep(FIBONACCI[attempt] * 1000);
                } catch (InterruptedException ex) {
                    throw new RuntimeException(e);
                }
            }
        }

    }


    private static void performWriteOperation(MongoCollection<Document> collection)  {
        List<Document> documentList = getDocumentsForBulkWrite();
        Iterator<Document> documentListIterator = documentList.iterator();
        while (documentListIterator.hasNext()) {
            collection.insertOne(documentListIterator.next());
        }
    }

    private static List<Document> getDocumentsForBulkWrite() {
        int docCount = 20;
        List<Document> documentList = new ArrayList<Document>();
        Faker faker = new Faker();
        Document document;
        for (int i = 0; i < docCount; i++) {
            document = new Document();
            document.put("name", faker.name().fullName());
            document.put("address", faker.address().streetAddress());
            document.put("age", faker.number().numberBetween(10, 90));
            documentList.add(document);
        }


        return documentList;
    }


}
