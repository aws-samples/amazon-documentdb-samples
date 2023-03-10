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

package software.amazon.documentdb.springboot;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.data.mongodb.repository.config.EnableMongoRepositories;
import software.amazon.documentdb.springboot.repository.LocationRepository;

@SpringBootApplication
@EnableMongoRepositories
public class DocDBSpringBootApplication {

  @Autowired
  LocationRepository localationRepository;

	public static void main(String[] args) {
		SpringApplication.run(DocDBSpringBootApplication.class, args);
	}

}
