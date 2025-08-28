// Local Ollama-powered Amazon DocumentDB TSQL Plugin for mongosh
const fs = require('fs');
const path = require('path');
const os = require('os');

// Load unsupported operators for use in Ollama prompt
function getDocumentDBConstraints() {
  try {
    const constraintsPath = path.join(os.homedir(), '.mongosh', 'documentdb-constraints.json');
    const constraintsData = JSON.parse(fs.readFileSync(constraintsPath, 'utf8'));
    return constraintsData.unsupported_operators || [];
  } catch (error) {
    return [];
  }
}

// Validate returned mongosh code before execution
function validateMongoCode(code) {
  const dangerous = [/require\s*\(/, /import\s+/, /process\s*\./, /global/, /Function\s*\(/, /setTimeout/, /setInterval/, /fs\./];
  const mongoPattern = /^db\.[\w.()\[\]{},"'\s$:_\-\/\\^]+$/s;
  return !dangerous.some(pattern => pattern.test(code)) && mongoPattern.test(code);
}

globalThis.tsql = async function(query, options = {}) {
  const { autoExecute = true } = options;
  const constraints = getDocumentDBConstraints();
  const constraintText = constraints.length > 0 
    ? `\n\nDocumentDB 5.0 constraints - DO NOT USE: ${constraints.join(', ')}`
    : '';

  const prompt = `Convert this TSQL query to MongoDB JavaScript code compatible with Amazon DocumentDB 5.0. Return ONLY the MongoDB code, no explanations:

TSQL: ${query}${constraintText}

Examples:
TSQL: SELECT * FROM users
MongoDB: db.users.find()

TSQL: SELECT name, age FROM users WHERE age > 25
MongoDB: db.users.find({age: {$gt: 25}}, {name: 1, age: 1})

TSQL: SELECT device, COUNT(*) FROM users GROUP BY device
MongoDB: db.users.aggregate([{$group: {_id: "$device", count: {$sum: 1}}}])

TSQL: SELECT u.name, p.title FROM users u JOIN posts p ON u.id = p.user_id
MongoDB: db.users.aggregate([{$lookup: {from: 'posts', localField: '_id', foreignField: 'user_id', as: 'posts'}}, {$unwind: '$posts'}, {$project: {name: 1, title: '$posts.title'}}])

MongoDB code:`;
  
  try {
    const response = await fetch('http://localhost:11434/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'codellama:7b',
        prompt: prompt,
        stream: false,
        options: { temperature: 0 }
      })
    });
    
    const data = await response.json();
    
    if (!data.response) {
      print('Error: No response from LLM');
      return null;
    }
    
    let mongoCode = data.response;
    
    const codeMatch = mongoCode.match(/```[^`]*\n(db\.[^`]+)\n```/);
    if (codeMatch) {
      mongoCode = codeMatch[1].trim();
    } else {
      const dbMatch = mongoCode.match(/db\.[^;\n}]+[})]*/);
      if (dbMatch) {
        mongoCode = dbMatch[0];
      }
    }
    
    print(`mongosh: ${mongoCode}`);
    
    // Review mode - return mongosh commands without executing
    if (!autoExecute) {
      print("> REVIEW MODE - COMMANDS NOT EXECUTED");
      return mongoCode;
    }
    
    // Clean up Ollama's returned code
    const cleanCode = mongoCode
      .replace(/```javascript|```js|```/g, '')
      .replace(/^MongoDB:\s*/i, '')
      .replace(/;$/, '')
      .replace(/\$count:\s*\{\}/g, '$sum: 1')
      .trim();
    
    if (!validateMongoCode(cleanCode)) {
      throw new Error('Invalid or potentially unsafe mongosh code');
    }
    
    // Try direct execution without eval for chained methods
    if (cleanCode.includes('.find(') && cleanCode.includes('.sort(')) {
      
      // find().sort() need to be parsed and executed step by step
      const match = cleanCode.match(/db\.(\w+)\.find\(([^)]*)\)\.sort\(([^)]*)\)/);
      if (match) {
        const [, collection, findArgs, sortArgs] = match;
        const cursor = db[collection].find(eval(`(${findArgs})`));
        return cursor.sort(eval(`(${sortArgs})`));
      }
    }
    
    // ObjectId conversion for _id fields
    if (cleanCode.includes('_id') && !cleanCode.includes('ObjectId')) {
      let convertedCode = cleanCode.replace(/"_id"\s*:\s*"([^"]+)"/g, '_id: ObjectId("$1")');
      convertedCode = convertedCode.replace(/_id\s*:\s*'([^']+)'/g, '_id: ObjectId("$1")');
      if (convertedCode !== cleanCode) {
        return eval(convertedCode);
      }
    }
    
    // Fallback to regular eval
    return eval(cleanCode);
  } catch (error) {
    print(`Error: ${error.message}`);
    return null;
  }
};

print("Local Ollama-Powered Amazon DocumentDB TSQL Plugin for mongosh loaded!");
print("Usage: tsql('SELECT * FROM users WHERE age > 25')");
print("Review mode: tsql('SELECT * FROM users', {autoExecute: false})");