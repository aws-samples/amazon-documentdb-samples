/*
  Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.

  Licensed under the Apache License, Version 2.0 (the "License").
  You may not use this file except in compliance with the License.
  A copy of the License is located at

      http://www.apache.org/licenses/LICENSE-2.0

  or in the "license" file accompanying this file. This file is distributed
  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
  express or implied. See the License for the specific language governing
  permissions and limitations under the License.
*/

package com.example.morphia.docdb;

import com.mongodb.client.MongoClients;
import com.mongodb.client.model.ReturnDocument;

import dev.morphia.Datastore;
import dev.morphia.Morphia;
import dev.morphia.DeleteOptions;
import dev.morphia.ModifyOptions;

import dev.morphia.query.FindOptions;
import dev.morphia.query.experimental.filters.Filters;
import dev.morphia.query.experimental.updates.UpdateOperators;

import java.util.List;
import java.util.ArrayList;

import com.example.morphia.docdb.entities.Product;


/**
 * Sample application with examples for CRUD operations with 
 * Morphia ODM library
 *
 */
public class App 
{
    static String KEY_STORE_TYPE = "/tmp/certs/rds-truststore.jks";
    static String DEFAULT_KEY_STORE_PASSWORD = "changeit";
    
    // Update below line with your cluster specific details. 
    static String docdb_uri = "mongodb://<user name>:<password>@<cluster endpoint>:27017/?ssl=true&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false";
    
    static String database_name = "catalog";
    
    static Datastore datastore = null;


    /*  Create the initial Morphia instance. 
    Using this instance, you can configure various aspects of how Morphia 
    maps your entities and validates your queries.
    */
    public static void setUp() {
        //
        setSslProperties();
        // A datastore instance for establishing a connection to Amazon DoocumentDB
        datastore = Morphia.createDatastore(MongoClients.create(docdb_uri), database_name);
        
        // Instruct Morphia, where to find your entity classes. 
        // Following line can be called multiple times with different packages or classes
        // can be called multiple times with different packages or classes
        datastore.getMapper().mapPackage("com.example.morphia.docdb");
        datastore.ensureIndexes();
    }

    
    // set the keystore for establishing a secure TLS connection 
    private static void setSslProperties() { 
        System.setProperty("javax.net.ssl.trustStore",  KEY_STORE_TYPE);
        System.setProperty("javax.net.ssl.trustStorePassword",  DEFAULT_KEY_STORE_PASSWORD);
    }
    
    // Save documents to a collection 
    public static void saveProducts() {
 
    	datastore.save(new Product("RayBan Sunglass Pro", "1590234","RayBan Sunglasses for professional sports people", 100, "fashion"));
    	datastore.save(new Product("GUCCI Handbag", "3451290", "Fashion Hand bags for all ages", 75, "fashion"));
    	datastore.save(new Product("Round hat", "8976045", "", 200, "fashion"));
    	datastore.save(new Product("Polo shirt", "6497023", "Cool shirts for hot summer", 25, "cloth"));
    	datastore.save(new Product("Swim shorts", "8245352", "Designer swim shorts for athletes", 200, "cloth"));
    	datastore.save(new Product("Running shoes", "3243662", "Shoes for work out and trekking", 20, "footware"));
    	
    	System.out.println(" Save complete ");
            
    }
    
    // Count number of documents in the collection  
    public static long getCount() {
        long count = datastore.find(Product.class).count();
        System.out.println(" Total number of products : "+count);
        return count;
    }

   // Find a document based on a key  
   public static Product findProductByName (String name) {
    	System.out.println(" Getting product by name : " + name);
    	Product product = datastore.find(Product.class).filter(
    	    Filters.eq("name", name)).iterator(new FindOptions().limit(1))
    	    .tryNext();
    	System.out.println(product);
    	return product; 
    }
    
    // List all the documents by a key 
    public static List<Product> findAllProductsByCategory(String category) {
    	List<Product> productList = datastore.find(Product.class).filter(
    	    Filters.eq("category", category)).iterator().toList();
    	System.out.println(productList);
    	return productList;
    }
    
    // Update a document identified by a key 
    public static void updateInventory(String sku) {
        System.out.println(" Updating Inventory for product by sku: " + sku);
        final Product updatedProduct = datastore.find(Product.class)
                    .filter(Filters.eq("sku", sku))
                    .modify(UpdateOperators.inc("inventory", 10))
                    .execute(new ModifyOptions().returnDocument(ReturnDocument.AFTER));
        System.out.println(" Updated product: " + updatedProduct);
    
    }
    
    // Delete a document identified by a key 
    public static void deleteProduct(String sku) {
    	datastore.find(Product.class)
                .filter(Filters.eq("sku", sku))
                .delete(new DeleteOptions().multi(true));
        System.out.println("Product with sku " + sku + " deleted");
    }

    // Delete all the documents in a collection  
    public static void deleteAll() {
    	datastore.find(Product.class)
                .delete(new DeleteOptions().multi(true));
    	System.out.println("All Products deleted.");
    }

    // main method to invoke example snippets 
    public static void main( String[] args )
    {
        
        setUp();
        
        System.out.printf("%n Insert few products : %n");
        System.out.println("-------------------------------");
        saveProducts();
        
        System.out.printf("%n Count all products : %n");
        System.out.println("-------------------------------");
        getCount();
        
        
        System.out.printf("%n Get product by name : %n");
        System.out.println("-------------------------------");
        findProductByName("GUCCI Handbag");
        

        System.out.printf("%n Get all products by category : %n");
        System.out.println("---------------------------------------");
        findAllProductsByCategory("fashion");
        
        System.out.printf("%n Update Inventory for Product by sku :  %n");
        System.out.println("-----------------------------------------------");
        updateInventory("3451290");
        
        System.out.printf("%n Delete product by sku  %n");
        System.out.println("-------------------------------");
        deleteProduct("1590234"); 
        
        System.out.printf("%n Deleting all products/documents  %n");
        System.out.println("-----------------------------------------");
        deleteAll(); 
        
    }
    
}
