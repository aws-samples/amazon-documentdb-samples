package com.example.documentdb.repository;

import java.util.List;

import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.data.mongodb.repository.Query;

import com.example.documentdb.model.Product;


public interface ProductRepository extends MongoRepository<Product, String> {
    
    @Query("{name:'?0'}")
    Product findProductByName(String name);
    
    @Query(value="{sku:'?0'}", fields="{'name' : 1, 'inventory' : 1}")
    Product findProductBySKU (String sku);   

    @Query("{category:'?0'}")
    List<Product> findAllByCategory(String category);
    
    
   
}