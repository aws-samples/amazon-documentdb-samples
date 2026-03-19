package com.example.documentdb.service;

import java.util.ArrayList;
import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.example.documentdb.model.Product;
import com.example.documentdb.repository.ProductRepository;

@Service
public class ProductService {
    
    @Autowired
	private ProductRepository productRepo;

    public void saveProducts() {
        
      	productRepo.save(new Product("RayBan Sunglass Pro", "1590234","RayBan Sunglasses for professional sports people", 100, "fashion"));
		productRepo.save(new Product("GUCCI Handbag", "3451290", "Fashion Hand bags for all ages", 75, "fashion"));
		productRepo.save(new Product("Round hat", "8976045", "", 200, "fashion"));
		productRepo.save(new Product("Polo shirt", "6497023", "Cool shirts for hot summer", 25, "cloth"));
		productRepo.save(new Product("Swim shorts", "8245352", "Designer swim shorts for athletes", 200, "cloth"));
		productRepo.save(new Product("Running shoes", "3243662", "Shoes for work out and trekking", 20, "footware"));
		
		System.out.println(" Save complete ");
        
    }
    
    /**
     * Count all products
     *
     */
    
    public long getCount() {
		long count = productRepo.count();
		System.out.println(" Total number of products : "+count);
		return count;
	}

	
	/**
     * Get product by name
     *
     */

	 public Product getProductByName(String name) {
		 System.out.println(" Getting product by name : " + name);
		 Product product = productRepo.findProductByName(name);
		 System.out.println(product);
		 return product; 
	 }
	 
	/**
     * Get product by sku
     *
     */
	 
	 public Product getProductBySKU(String sku) {
		 System.out.println(" Getting product by SKU : " + sku);
		 Product product = productRepo.findProductBySKU(sku);
		 System.out.println(product);
		 return product; 
	 }
	 
    /**
     * Find all the products by category 
     *
     */
     
	 public List<Product> findAllProductsByCategory(String category) {
	 	List<Product> productList = productRepo.findAllByCategory(category);
		productList.forEach(product -> System.out.println(product));
		return productList;
	 }
	 
	 public void updateInventory(String sku) {
	 	Product product =  getProductBySKU(sku);
	 	
	 	System.out.println(" Updating Inventory for product by sku: " + sku);
	 	product.setInventory(product.getInventory()+10);
	 	Product updatedProd = productRepo.save(product);
	 	System.out.println(" Updated : " + updatedProd);
	 }
	 
	public void deleteProduct(String id) {
         productRepo.deleteById(id);
         System.out.println(" Product with id " + id + " deleted");
     }

    public void deleteAll() {
      productRepo.deleteAll();
      System.out.println(" All Products deleted.");
    }
	
    
}