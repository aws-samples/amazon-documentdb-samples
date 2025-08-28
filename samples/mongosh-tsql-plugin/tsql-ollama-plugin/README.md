# Local Ollama-Powered Amazon DocumentDB TSQL Plugin for mongosh
This AI-powered mongosh plugin translates TSQL queries into Amazon DocumentDB-compatible mongosh commands. This version is powered by [Ollama](https://ollama.com/) and runs locally on your machine. See [Amazon Bedrock-Powered Amazon DocumentDB TSQL Plugin for mongosh](https://github.com/aws-samples/amazon-documentdb-samples/tree/master/samples/mongosh-tsql-plugin/tsql-bedrock-plugin) for the version powered by Amazon Bedrock and Claude 3 Haiku.

Both versions automatically handle [Supported MongoDB APIs, operations, and data types in Amazon DocumentDB](https://docs.aws.amazon.com/documentdb/latest/developerguide/mongo-apis.html), allow for customization of the prompt and LLM, and include a safety review mode to show generated code before execution.

## Prerequisites
1. Ollama installed locally
2. Python 3 for DocumentDB compatibility checking
3. Amazon DocumentDB compatibility tool (compat.py)

## Download Amazon DocumentDB Compatibility Tool
The setup script will prompt you for the local location of `compat.py`. This is included in the Amazon DocumentDB Compatibility Tool and can be accessed in the [amazon-documentdb-tools GitHub repository](https://github.com/awslabs/amazon-documentdb-tools/tree/master/compat-tool).

## Setup
```bash
# Run setup script (will prompt for compat.py location)
./setup-ollama-tsql.sh
```

## Example Usage

### 1. Select
```javascript
tsql(`SELECT *
FROM customers
WHERE trafficfrom = 'mysite.com'
ORDER BY trans_timestamp DESC;`)

//Output
mongosh: db.customers.find({trafficfrom: "mysite.com"}).sort({trans_timestamp: -1})
```

### 2. Select with Projection
```javascript
tsql(`SELECT custid, trafficfrom, device, touchproduct
FROM customers
WHERE device = 'app_mobile'
AND trans_timestamp >= '2025-09-20';`)

//Output
mongosh: db.customers.find({ device: "app_mobile", trans_timestamp: { $gte: new Date("2025-09-20") } })
```

### 3. Aggregation with GROUP BY
```javascript
tsql(`SELECT device, COUNT(*) as visit_count
FROM customers
GROUP BY device;`)

//Output
mongosh: db.customers.aggregate([{$group: {_id: "$device", visit_count: {$sum: 1}}}])
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

## Key Features
- **Complete Privacy**: All processing happens locally
- **No API Costs**: Free after initial setup
- **Offline Capable**: Works without internet connection
- **Amazon DocumentDB Compatibility**: Built-in compatibility checking

## Requirements
- **Storage**: ~4GB for CodeLlama 7B model

## Customizing the Model
The plugin uses CodeLlama 7B by default, but you can switch to other models:

```bash
# Install a different model
ollama pull codellama:13b       # Larger, more accurate (7GB)
ollama pull llama2:7b           # General purpose alternative
ollama pull mistral:7b          # Faster, smaller model

# Edit tsql-ollama-plugin.js and change the model line:
model: 'codellama:13b',  # Changed from 'codellama:7b'
```

**Model Trade-offs:**
- **Larger models** (13B+): More accurate but slower and uses more memory
- **Smaller models** (7B): Faster but may be less accurate on complex queries
- **Specialized models**: CodeLlama is optimized for code generation

## Customizing the Prompt

You can modify the prompt in `tsql-ollama-plugin.js` to improve results for your specific use case:

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

⚠️ **Review All Generated Code**: This tool uses AI to translate queries and may produce incorrect results. Always review the generated mongosh code before executing it against production data.

⚠️ **Test First**: Test generated queries on sample data before running against production databases.

⚠️ **Complex Queries**: More complex TSQL queries may require manual review and adjustment of the generated mongosh code.


**Best Practices:**
- **Use review mode**: `tsql(query, {autoExecute: false})`
- Start with simple queries to understand the tool's behavior
- Keep a backup of important data before running generated queries
- Use the tool as a starting point, not a final solution
- Verify results match your expectations