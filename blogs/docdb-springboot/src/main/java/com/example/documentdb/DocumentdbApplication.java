package com.example.documentdb;


import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import com.example.documentdb.repository.ProductRepository;
import com.example.documentdb.service.ProductService;


@SpringBootApplication
public class DocumentdbApplication implements CommandLineRunner{

	@Autowired
    private ProductService prodService;

	public static void main(String[] args) {
		SpringApplication.run(DocumentdbApplication.class, args);
	}

	@Override
	public void run(String... args) throws Exception {
		
		System.out.printf("%n Insert few products : %n");
		System.out.println("-------------------------------");
		prodService.saveProducts();
		
		System.out.printf("%n Count all products : %n");
		System.out.println("-------------------------------");
		prodService.getCount();
		
		
		System.out.printf("%n Get product by name : %n");
		System.out.println("-------------------------------");
		prodService.getProductByName("GUCCI Handbag");
		
		System.out.printf("%n Get product by sku : %n");
		System.out.println("-------------------------------");
		prodService.getProductBySKU("8976045");
		
		System.out.printf("%n Get all products by category : %n");
		System.out.println("---------------------------------------");
		prodService.findAllProductsByCategory("fashion");
		
		System.out.printf("%n Update Inventory for Product by sku :  %n");
		System.out.println("-----------------------------------------------");
		prodService.updateInventory("3451290");
		
		System.out.printf("%n Delete product id  %n");
		System.out.println("-------------------------------");
		prodService.deleteProduct("639a0046efe46b7343dd5004"); 
		
		System.out.printf("%n Deleting all products/documents  %n");
		System.out.println("-----------------------------------------");
		prodService.deleteAll(); 
	}

}
