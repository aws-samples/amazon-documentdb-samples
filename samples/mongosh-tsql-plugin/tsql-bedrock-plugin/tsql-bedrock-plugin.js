// Amazon Bedrock-powered Amazon DocumentDB TSQL Plugin for mongosh
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

// Load unsupported operators for use in Bedrock prompt
const tsqlBedrockPlugin = {
  getDocumentDBConstraints() {
    try {
      const constraintsPath = path.join(os.homedir(), '.mongosh', 'documentdb-constraints.json');
      const constraintsData = JSON.parse(fs.readFileSync(constraintsPath, 'utf8'));
      return constraintsData.unsupported_operators || [];
    } catch (error) {
      return [];
    }
  },
  
// Call Amazon Bedrock to translate TSQL to MongoDB
  async translateWithBedrock(tsqlQuery) {
    const constraints = this.getDocumentDBConstraints();
    const constraintText = constraints.length > 0 
      ? `\n\nDocumentDB 5.0 constraints - DO NOT USE: ${constraints.join(', ')}`
      : '';

    const prompt = `Convert this TSQL query to MongoDB JavaScript code compatible with Amazon DocumentDB 5.0. Return ONLY the MongoDB code, no explanations:

TSQL: ${tsqlQuery}${constraintText}

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
      const body = {
        messages: [{
          role: "user",
          content: prompt
        }],
        max_tokens: 550,
        anthropic_version: "bedrock-2023-05-31"
      };
      
      const bodyFile = path.join(os.tmpdir(), `bedrock-body-${Date.now()}-${Math.random().toString(36).substr(2, 9)}.json`);
      const responseFile = path.join(os.tmpdir(), `bedrock-response-${Date.now()}-${Math.random().toString(36).substr(2, 9)}.json`);
      
      fs.writeFileSync(bodyFile, JSON.stringify(body));
      
      const command = `aws bedrock-runtime invoke-model --model-id anthropic.claude-3-haiku-20240307-v1:0 --body file://${bodyFile} --cli-binary-format raw-in-base64-out ${responseFile}`;
      
      execSync(command, { stdio: 'pipe' });
      
      const response = JSON.parse(fs.readFileSync(responseFile, 'utf8'));
      
      // Clean up temporary files
      try {
        fs.unlinkSync(bodyFile);
        fs.unlinkSync(responseFile);
      } catch (cleanupError) {
      }
      return response.content[0].text.trim();
    } catch (error) {
      if (error.message.includes('aws') || error.message.includes('credentials')) {
        throw new Error('AWS Bedrock service unavailable');
      }
      throw new Error('Translation service error');
    }
  }
};

// Validate returned mongosh code before running
function validateMongoCode(code) {
  const dangerous = [/require\s*\(/, /import\s+/, /process\s*\./, /global/, /Function\s*\(/, /setTimeout/, /setInterval/, /fs\./];
  const mongoPattern = /^db\.[\w.()\[\]{},"'\s$:_\-\/\\^]+$/s;
  return !dangerous.some(pattern => pattern.test(code)) && mongoPattern.test(code);
}

globalThis.tsql = async function(query, options = {}) {
  const { autoExecute = true } = options;
  try {
    const mongoCode = await tsqlBedrockPlugin.translateWithBedrock(query);
    print(`mongosh: ${mongoCode}`);
    
    // Review mode - return mongosh commands without executing
    if (!autoExecute) {
      print("> REVIEW MODE - COMMANDS NOT EXECUTED");
      return mongoCode;
    }
    
    // Clean up Bedrock's returned code
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
    let safeMessage = 'Query processing failed';
    if (error.message.includes('Invalid or potentially unsafe')) {
      safeMessage = 'Invalid query format';
    } else if (error.message.includes('Bedrock') || error.message.includes('Translation')) {
      safeMessage = 'Translation service unavailable';
    } else if (error.message.includes('SyntaxError')) {
      safeMessage = 'Invalid MongoDB syntax generated';
    }
    print(`Error: ${safeMessage}`);
    return null;
  }
};

print("Amazon Bedrock-Powered Amazon DocumentDB TSQL Plugin for mongosh loaded!");
print("Usage: tsql('SELECT * FROM users WHERE age > 25')");
print("Review mode: tsql('SELECT * FROM users', {autoExecute: false})");