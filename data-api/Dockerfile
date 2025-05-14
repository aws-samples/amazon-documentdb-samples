# Use the official Node.js LTS image as the base image
FROM node:22-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and yarn.lock to the working directory
COPY package.json yarn.lock ./

# Install dependencies
RUN yarn install --frozen-lockfile

# Copy the rest of the application code
COPY . .

# Build the application
RUN yarn build

# Expose the application port
EXPOSE 3000

# Set the environment variable for production
ENV NODE_ENV=production

# Start the application
CMD ["yarn", "start:prod"]