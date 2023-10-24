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

package com.example.morphia.docdb.entities;

import dev.morphia.annotations.Entity;
import dev.morphia.annotations.Id;
import org.bson.types.ObjectId;

@Entity("products")
public class Product {

    @Id
    private ObjectId id;    
    
    /** 
     * Set up data Members that correspond to fields in the products collection
     */
     
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
    public Product(String name, String sku, String description, int inventory, String category) {
        
        this.name = name;
        this.sku = sku;
        this.description = description;
        this.inventory = inventory;
        this.category = category;
    }
    // getters, setters and toString implementations


    /**
     * @return the id
     */
    public ObjectId getId() {
        return id;
    }


    /**
     * @param id the id to set
     */
    public void setId(ObjectId id) {
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
    
    @Override
    public String toString() {
       return " Product [id=" + id  + ", name=" + name + ", sku=" + sku +  
        ", description=" + description  + ", inventory=" +  inventory + 
        ", category=" + category + "]";
    }
}