package com.example.documentdb.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

@Document(collection = "products")
public class Product {

    @Id
    private String id;    
    
   //Set up Data Members that correspond to columns in the Music table
    private String name;
    private String sku;
    private String description;
    private int inventory;
    private String category;
    

    /**
     * @param id
     * @param name
     * @param sku
     * @param description
     * @param inventory
     * @param category
     */
    public Product(String id, String name, String sku, String description, int inventory, String category) {
        this.id = id;
        this.name = name;
        this.sku = sku;
        this.description = description;
        this.inventory = inventory;
        this.category = category;
    }
    
     /**
     * @param name
     * @param sku
     * @param description
     * @param inventory
     * @param category
     */
    public Product(String name, String sku, String description, int inventory, String category) {
        this.name = name;
        this.sku = sku;
        this.description = description;
        this.inventory = inventory;
        this.category = category;
    }
    
    public Product() {
        
    }
    
    /**
     * @return the id
     */
    public String getId() {
        return id;
    }

    /**
     * @param id the id to set
     */
    public void setId(String id) {
        this.id = id;
    }
   
     /**
     * @return the name
     */
    public String getName() {
        return name;
    }
    
    /**
     * @param name the name to set
     */
    public void setName(String name) {
        this.name = name;
    }

    /**
     * @return the description
     */
    public String getDescription() {
        return description;
    }

    /**
     * @param description the description to set
     */
    public void setDescription(String description) {
        this.description = description;
    }

    /**
     * @return the sku
     */
    public String getSku() {
        return sku;
    }

    /**
     * @param sku the sku to set
     */
    public void setSku(String sku) {
        this.sku = sku;
    }

     /**
     * @return the category
     */
    public String getCategory() {
        return category;
    }

    /**
     * @param category the category to set
     */
    public void setCategory(String category) {
        this.category = category;
    }
    
    /**
     * @return the inventory
     */
    public int getInventory() {
        return inventory;
    }

    /**
     * @param inventory the inventory to set
     */
    public void setInventory(int inventory) {
        this.inventory = inventory;
    }
    
    
    
     /* (non-Javadoc)
     * @see java.lang.Object#toString()
     */
    
    @Override
    public String toString() {
        return " Product [id=" + id  + ", name=" + name + ", sku=" + sku +  
        ", description=" + description  + ", inventory=" +  inventory + 
        ", category=" + category + "]";
    }

}