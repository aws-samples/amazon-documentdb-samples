import os
import sys
import logging

import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError, ServerSelectionTimeoutError
from flask import Flask, render_template, request, jsonify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def _sanitize_error(e: Exception) -> str:
    """Return a generic message for unexpected errors to avoid leaking internals."""
    if isinstance(e, (ValueError, KeyError)):
        return str(e)
    return "An internal error occurred. Check the server logs for details."

_client = None

def get_config() -> dict:
    """Load connection configuration from environment variables."""
    required = ["DOCDB_HOST", "DOCDB_USERNAME", "DOCDB_PASSWORD", "DOCDB_TLS_CA"]
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        logger.error("Missing required environment variables: %s", missing)
        sys.exit(1)

    return {
        "host": os.environ["DOCDB_HOST"],
        "port": int(os.environ.get("DOCDB_PORT", 27017)),
        "username": os.environ["DOCDB_USERNAME"],
        "password": os.environ["DOCDB_PASSWORD"],
        "tls_ca_file": os.environ["DOCDB_TLS_CA"],
    }


def get_client():
    """Get DocumentDB client connection."""
    global _client
    if _client is None:
        config = get_config()
        
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                _client = MongoClient(
                    host=config["host"],
                    port=config["port"],
                    username=config["username"],
                    password=config["password"],
                    tls=True,
                    tlsCAFile=config["tls_ca_file"],
                    retryWrites=False,
                    maxPoolSize=10,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                    socketTimeoutMS=10000,
                )

                _client.admin.command('ping')
                logger.info("Connected to DocumentDB")
                break
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Connection attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"Failed to connect after {max_retries} attempts")
                    raise
    
    return _client

def get_collection():
    """Get products collection."""
    try:
        client = get_client()
        db = client["product_catalog"]
        return db["products"]
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error("Failed to connect to DocumentDB: %s", e)
        raise

def ensure_indexes(collection: pymongo.collection.Collection) -> None:
    """Create indexes for product catalog queries."""
    collection.create_index("sku", unique=True, name="idx_sku_unique")
    collection.create_index("category", name="idx_category")
    collection.create_index("name", name="idx_name")
    collection.create_index([("name", "text")], name="idx_text_search")
    logger.info("Indexes ensured on collection '%s'.", collection.name)

@app.route('/')
def index():
    """Display all products."""
    collection = get_collection()
    
    pipeline = [
        {"$addFields": {"in_stock": {"$gt": ["$stock", 0]}}},
        {"$project": {"_id": 0}},
        {"$sort": {"category": 1}}
    ]
    
    products = list(collection.aggregate(pipeline))
    categories = collection.distinct("category")
    return render_template('index.html', products=products, categories=categories)

@app.route('/api/products', methods=['GET'])
def get_products():
    """Get all products."""
    collection = get_collection()
    category = request.args.get('category')
    search = request.args.get('search')
    limit = int(request.args.get('limit', 100))
    cursor = request.args.get('cursor')
    limit = min(limit, 1000)
    
    query = {}
    if category:
        query['category'] = category
    if search:
        query['$text'] = {'$search': search}
    
    if cursor:
        query['name'] = {'$gt': cursor}
    
    try:
        products = list(collection.find(
            query,
            {'_id': 0}
        ).sort('name', 1).limit(limit + 1))
        
        for product in products:
            product['in_stock'] = product.get('stock', 0) > 0
        
        has_more = len(products) > limit
        if has_more:
            products = products[:limit]
        
        next_cursor = products[-1]['name'] if products and has_more else None
        
        return jsonify({
            "products": products,
            "pagination": {
                "limit": limit,
                "next_cursor": next_cursor,
                "has_more": has_more
            }
        })
    except Exception as e:
        logger.error("Error in get_products: %s", e)
        return jsonify({"success": False, "message": _sanitize_error(e)}), 500

@app.route('/api/products', methods=['POST'])
def add_product():
    """API endpoint to add a new product."""
    data = request.json
    collection = get_collection()
    
    try:
        price = float(data['price'])
        stock = int(data['stock'])
        
        if price < 0:
            return jsonify({"success": False, "message": "Price cannot be negative"}), 400
        if stock < 0:
            return jsonify({"success": False, "message": "Stock cannot be negative"}), 400
        
        product = {
            "sku": data['sku'],
            "name": data['name'],
            "category": data['category'],
            "price": price,
            "stock": stock,
        }
        
        if 'description' in data and data['description']:
            product['description'] = data['description']
        
        collection.insert_one(product)
        logger.info("Added product: %s (SKU: %s)", product['name'], product['sku'])
        return jsonify({"success": True, "message": "Product added successfully"})
    except DuplicateKeyError:
        return jsonify({"success": False, "message": "Product with this SKU already exists"}), 400
    except (ValueError, KeyError) as e:
        return jsonify({"success": False, "message": f"Invalid input: {_sanitize_error(e)}"}), 400
    except Exception as e:
        logger.error("Error adding product: %s", e)
        return jsonify({"success": False, "message": _sanitize_error(e)}), 500

@app.route('/api/products/<sku>', methods=['PUT'])
def update_product(sku):
    """API endpoint to update a product."""
    data = request.json
    collection = get_collection()
    
    try:
        price = float(data['price'])
        stock = int(data['stock'])
        
        if price < 0:
            return jsonify({"success": False, "message": "Price cannot be negative"}), 400
        if stock < 0:
            return jsonify({"success": False, "message": "Stock cannot be negative"}), 400
        
        update_fields = {
            "name": data['name'],
            "category": data['category'],
            "price": price,
            "stock": stock,
        }
        
        if 'description' in data:
            update_fields['description'] = data['description']
        
        result = collection.update_one(
            {"sku": sku},
            {"$set": update_fields}
        )
        
        if result.matched_count == 0:
            return jsonify({"success": False, "message": "Product not found"}), 404
        
        logger.info("Updated product: %s", sku)
        return jsonify({"success": True, "message": "Product updated successfully"})
    except (ValueError, KeyError) as e:
        return jsonify({"success": False, "message": f"Invalid input: {_sanitize_error(e)}"}), 400
    except Exception as e:
        logger.error("Error updating product: %s", e)
        return jsonify({"success": False, "message": _sanitize_error(e)}), 500

@app.route('/api/products/<sku>/stock', methods=['PUT'])
def update_stock(sku):
    """API endpoint to update product stock."""
    data = request.json
    collection = get_collection()
    
    try:
        quantity_change = int(data['change'])
        
        product = collection.find_one({"sku": sku}, {"stock": 1})
        if product is None:
            return jsonify({"success": False, "message": "Product not found"}), 404
        
        new_stock = product["stock"] + quantity_change
        if new_stock < 0:
            return jsonify({"success": False, "message": f"Insufficient stock. Current: {product['stock']}, Requested change: {quantity_change}"}), 400
        
        result = collection.update_one(
            {"sku": sku},
            {"$inc": {"stock": quantity_change}}
        )
        
        logger.info("Updated stock for SKU %s by %d", sku, quantity_change)
        return jsonify({"success": True, "message": "Stock updated successfully"})
    except (ValueError, KeyError) as e:
        return jsonify({"success": False, "message": f"Invalid input: {_sanitize_error(e)}"}), 400
    except Exception as e:
        logger.error("Error updating stock: %s", e)
        return jsonify({"success": False, "message": _sanitize_error(e)}), 500

@app.route('/api/products/<sku>/description', methods=['PUT'])
def update_description(sku):
    """API endpoint to update product custom description fields."""
    data = request.json
    collection = get_collection()
    
    try:
        description = data.get('description', {})
        result = collection.update_one(
            {"sku": sku},
            {"$set": {"description": description}}
        )
        
        if result.matched_count == 0:
            return jsonify({"success": False, "message": "Product not found"}), 404
        
        logger.info("Updated description for SKU %s", sku)
        return jsonify({"success": True, "message": "Description updated successfully"})
    except Exception as e:
        logger.error("Error updating description: %s", e)
        return jsonify({"success": False, "message": _sanitize_error(e)}), 500

@app.route('/api/products/<sku>', methods=['DELETE'])
def delete_product(sku):
    """API endpoint to delete a product."""
    collection = get_collection()
    
    try:
        result = collection.delete_one({"sku": sku})
        if result.deleted_count == 0:
            return jsonify({"success": False, "message": "Product not found"}), 404
        
        logger.info("Deleted product with SKU: %s", sku)
        return jsonify({"success": True, "message": "Product deleted successfully"})
    except Exception as e:
        logger.error("Error deleting product: %s", e)
        return jsonify({"success": False, "message": _sanitize_error(e)}), 500

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """API endpoint to get aggregation analytics."""
    collection = get_collection()
    
    try:
        pipeline = [
            {
                "$group": {
                    "_id": "$category",
                    "count": {"$sum": 1},
                    "total_value": {"$sum": {"$multiply": ["$price", "$stock"]}},
                    "low_stock_count": {
                        "$sum": {"$cond": [{"$lte": ["$stock", 10]}, 1, 0]}
                    }
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "category": "$_id",
                    "count": 1,
                    "total_value": 1
                }
            },
            {"$sort": {"total_value": -1}}
        ]
        
        results = list(collection.aggregate(pipeline))
        
        total_value = sum(r['total_value'] for r in results)
        total_products = sum(r['count'] for r in results)
        low_stock_count = collection.count_documents({"stock": {"$lte": 10}})
        
        return jsonify({
            "by_category": results,
            "total_value": total_value,
            "total_products": total_products,
            "low_stock_count": low_stock_count
        })
    except Exception as e:
        logger.error("Error getting analytics: %s", e)
        return jsonify({"success": False, "message": _sanitize_error(e)}), 500

if __name__ == "__main__":
    # Initialize indexes on startup
    try:
        collection = get_collection()
        ensure_indexes(collection)
        
        # Seed database with sample products if empty
        if collection.count_documents({}) == 0:
            import csv
            logger.info("Seeding database with sample products...")
            with open('seed_data.csv', 'r') as f:
                reader = csv.DictReader(f)
                products = []
                for row in reader:
                    products.append({
                        "sku": row['sku'],
                        "name": row['name'],
                        "category": row['category'],
                        "price": float(row['price']),
                        "stock": int(row['stock']),
                    })
                collection.insert_many(products)
                logger.info("Inserted %d sample products", len(products))
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error("Cannot start application - DocumentDB connection failed: %s", e)
        logger.error("Please check your connection settings and ensure DocumentDB is accessible")
        sys.exit(1)
    
    # Run app
    logger.info("Starting web interface on http://localhost:5000")
    # debug=True is intentional for this demo/sample application.
    # Disable debug mode when adapting this code for production use.
    app.run(debug=True, host='0.0.0.0', port=5000)