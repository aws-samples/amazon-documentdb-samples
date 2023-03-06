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

package software.amazon.documentdb.springboot.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import software.amazon.documentdb.springboot.exception.ResourceNotFoundException;
import software.amazon.documentdb.springboot.model.Location;
import software.amazon.documentdb.springboot.repository.LocationRepository;

import java.util.List;
import java.util.Optional;

@Service
public class LocationService {

    @Autowired
    private LocationRepository locationRepository;

    public List<Location> getAllLocations() {
        return locationRepository.findAll();
    }

    public Location getLocationById(String id) throws ResourceNotFoundException {
        Optional<Location> optionalLocation = locationRepository.findById(id);
        if (optionalLocation.isPresent()) {
            return optionalLocation.get();
        } else {
            throw new ResourceNotFoundException("Location not found with id " + id);
        }
    }

    public Location createLocation(Location location) {
        return locationRepository.save(location);
    }

    public Location updateLocation(String id, Location updatedLocation) throws ResourceNotFoundException {
        Optional<Location> optionalLocation = locationRepository.findById(id);

        if (optionalLocation.isPresent()) {            
            return locationRepository.save(updatedLocation);
        } else {
            throw new ResourceNotFoundException("Location not found with id " + id);
        }
    }

    public void deleteLocation(String id) throws ResourceNotFoundException {
        Optional<Location> optionalLocation = locationRepository.findById(id);

        if (optionalLocation.isPresent()) {
            locationRepository.deleteById(id);
        } else {
            throw new ResourceNotFoundException("Location not found with id " + id);
        }
    }
}
