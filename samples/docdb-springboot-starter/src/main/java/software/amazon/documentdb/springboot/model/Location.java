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

package software.amazon.documentdb.springboot.model;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;
import org.springframework.data.mongodb.core.mapping.FieldType;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "locations")
public class Location {
    
    @Id    
    @org.springframework.data.mongodb.core.mapping.Field(targetType = FieldType.OBJECT_ID)
    private String id;
    
    @Field("URL")
    private String URL;
    
    @Field("name")
    private String name;
    
    @Field("address")
    private String address;
    
    @Field("address_line_2")
    private String addressLine2;
    
    @Field("outcode")
    private String outcode;
    
    @Field("postcode")
    private String postcode;
    
    @Field("rating")
    private float rating;
    
    @Field("type_of_food")
    private String typeOfFood;
}
