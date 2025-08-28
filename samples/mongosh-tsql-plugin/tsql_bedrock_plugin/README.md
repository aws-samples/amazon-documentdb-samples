# Amazon Bedrock-Powered Amazon DocumentDB TSQL Plugin for mongosh
This AI-powered mongosh plugin translates TSQL queries into Amazon DocumentDB-compatible mongosh commands. This version is powered by Amazon Bedrock  using Claude 3 Haiku. See **Local Ollama-Powered Amazon DocumentDB TSQL Plugin for mongosh** for the version that runs locally on your machine.

Both versions automatically handle [Supported MongoDB APIs, operations, and data types in Amazon DocumentDB](https://docs.aws.amazon.com/documentdb/latest/developerguide/mongo-apis.html), allow for customization of the prompt and LLM, and include a safety review mode to show generated code before execution.

## Prerequisites
1. AWS account with Bedrock access
2. AWS CLI configured with credentials
3. Bedrock model access (Claude 3 Haiku)
4. Amazon DocumentDB compatibility tool (compat.py)

## Download Amazon DocumentDB Compatibility Tool
The setup script will prompt you for the local ocation of `compat.py`. This is included in the Amazon DocumentDB Compatibility Tool and can be access in the [amazon-documentdb-tools GitHub repository](https://github.com/awslabs/amazon-documentdb-tools/tree/master/compat-tool).

## Setup
```bash
# Run setup script
./setup-bedrock-tsql.sh

# Configure AWS credentials if not already done
aws configure
# Enter: Access Key, Secret Key, Region (us-east-1), Output format (json)
```

## Enable Bedrock Model Access
Ensure you have access to `Anthropic Claude 3 Haiku (anthropic.claude-3-haiku-20240307-v1:0)`

Visit the [Amazon Bedrock User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html) to learn how to add access to foundation models.

## Example Usage

### 1. Select
```javascript
tsql(`SELECT *
FROM customers
WHERE trafficfrom = 'mysite.com'
ORDER BY trans_timestamp DESC;`)

//Output
mongosh: db.customers.find({trafficfrom: 'mysite.com'}).sort({trans_timestamp: -1});
```

### 2. Select
```javascript
tsql(`SELECT custid, trafficfrom, device, touchproduct
| FROM customers
| WHERE device = 'app_mobile'
| AND trans_timestamp >= '2025-09-20';`)

//Output
mongosh: db.customers.find({
  device: 'app_mobile',
  trans_timestamp: { $gte: new Date('2025-09-20') }
}, {
  custid: 1,
  trafficfrom: 1,
  device: 1,
  touchproduct: 1
})
```

### 3. Update
```javascript
tsql(`UPDATE customers
SET 
    trafficfrom = 'mysite.com',
    device = 'phone',
    product = 111
WHERE _id = '650b0a714c728dcb47f97853';`)

//Output
mongosh: db.customers.updateOne(
  { _id: ObjectId("650b0a714c728dcb47f97853") },
  { $set: {
    trafficfrom: 'mysite.com',
    device: 'phone',
    product: 111
  }}
)
```

### 4. Insert
```javascript
tsql(`INSERT INTO customers 
(custid, trafficfrom, url, device, product, trans_timestamp)
VALUES 
(22, 'mysite.com', 'new_orders', 'app_mobile', 126, '2025-09-20T15:06:24.506260');`)

//Output
mongosh: db.customers.insertOne({
    custid: 22,
    trafficfrom: 'mysite.com',
    url: 'new_orders',
    device: 'app_mobile',
    product: 126,
    trans_timestamp: new Date('2025-09-20T15:06:24.506260')
})
```

### 5. Delete
```javascript
tsql(`DELETE FROM customers
WHERE _id = '650b0bfa938593cca4d05b30';`)

//Output
mongosh: db.customers.deleteOne({_id: '650b0bfa938593cca4d05b30'});
```

### 6. Regex
```javascript
tsql(`SELECT * FROM customers
WHERE trafficfrom LIKE '%.com';`)

//Output
mongosh: db.customers.find({
  trafficfrom: {
    $regex: /\.com$/
  }
});
```

### 7. $lookup / inner join
```javascript
tsql(`SELECT 
    p.category,
    COUNT(o.order_number) as total_orders,
    SUM(o.quantity) as total_quantity_ordered,
    SUM(o.quantity * p.price) as total_revenue
FROM orders o
INNER JOIN products p 
    ON o.product_id = p._id
GROUP BY p.category
ORDER BY total_revenue DESC;`)

//Output
mongosh: db.orders.aggregate([
  {
    $lookup: {
      from: "products",
      localField: "product_id",
      foreignField: "_id",
      as: "product"
    }
  },
  {
    $unwind: "$product"
  },
  {
    $group: {
      _id: "$product.category",
      total_orders: {$sum: 1},
      total_quantity_ordered: {$sum: "$quantity"},
      total_revenue: {$sum: {$multiply: ["$quantity", "$product.price"]}}
    }
  },
  {
    $sort: {
      total_revenue: -1
    }
  }
])
```

## Review Mode
You can pass `autoExecute: false` to your `tsql` statements to run the query in reveiw mode. This will return the mongosh commend without automatically executing against your namespaces.
```javascript
// Review mode - shows generated code without executing
tsql(`SELECT * FROM customers WHERE age > 25`, {autoExecute: false})

// Output:
mongosh: db.customers.find({age: {$gt: 25}})
> REVIEW MODE - COMMANDS NOT EXECUTED
```

### Auto-Execute Mode
```javascript
// Direct execution (default)
tsql(`SELECT * FROM customers WHERE age > 25`)
```

## Amazon Bedrock Token Usage (Estimate)
| Component | Token Count |
|-----------|-------------|
| Base prompt text | ~50 tokens |
| TSQL query | ~10-50 tokens (variable) |
| Compatibility list | ~20-100 tokens |
| Prompt examples | ~300-350 tokens |
| **TOTAL** | **~380-550 tokens per request** |

## Customizing the Prompt

You can modify the prompt in `tsql-bedrock-plugin.js` to improve results for your specific use case:

```javascript
// Find this section in the file and modify as needed:
const prompt = `Convert this TSQL query to MongoDB JavaScript code...

// Add your own examples:
TSQL: SELECT * FROM your_table_name
MongoDB: db.your_table_name.find()

// Add domain-specific instructions:
Always use camelCase for field names.
Prefer $match over find() for complex queries.
`;
```

## Important Disclaimers

⚠️ **Review All Generated Code**: This tool uses AI to translate queries and may produce incorrect results. Always review the generated MongoDB code before executing it on production data.

⚠️ **Test First**: Test generated queries on sample data before running on production databases.

⚠️ **Complex Queries**: More complex TSQL queries may require manual review and adjustment of the generated MongoDB code.

⚠️ **DocumentDB Limitations**: While the tool attempts to generate DocumentDB-compatible code, some advanced MongoDB features may not work in DocumentDB.

**Best Practices:**
- **Use review mode by default**: `tsql(query, {autoExecute: false})`
- Start with simple queries to understand the tool's behavior
- Keep a backup of important data before running generated queries
- Use the tool as a starting point, not a final solution
- Verify results match your expectations