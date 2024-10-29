use std::{env, error::Error, path::PathBuf};
use serde::Deserialize;
use serde_json;
use mongodb::{Client, Database, options::{ClientOptions, TlsOptions, Tls}, bson::{doc, Document}};
use aws_config::BehaviorVersion;
use aws_sdk_secretsmanager::{Client as SecretsManagerClient, Error as SecretsError};

#[derive(Deserialize)]
struct DocumentDbSecret {
    username: String,
    password: String,
    host: String,
    port: u64,
}

//
// Function to retrieve credentials from AWS Secrets Manager
//
async fn get_secret(secret_name: &str) -> Result<DocumentDbSecret, SecretsError> {
    let config = aws_config::load_defaults(BehaviorVersion::latest()).await;
    let client = SecretsManagerClient::new(&config);

    let secret_value = client
        .get_secret_value()
        .secret_id(secret_name)
        .send()
        .await?;

    let secret_str = secret_value.secret_string().unwrap();
    let secret: DocumentDbSecret = serde_json::from_str(secret_str).unwrap();
    Ok(secret)
}

// 'C' of CRUD functions
async fn create_document(database: &Database) -> Result<(), Box<dyn Error>> {
    let collection = database.collection("mycollection");

    let document = doc! {
        "name": "Alice",
        "age": 30,
        "city": "Seattle"
    };

    collection.insert_one(document).await?;

    println!("Document inserted!");

    Ok(())
}
// 'R' of CRUD functions
async fn read_document(database: &Database) -> Result<(), Box<dyn Error>> {
    let collection = database.collection::<Document>("mycollection");

    let filter = doc! { 
        "name": "Alice"
    };

    let result = collection.find_one(filter).await?;

    println!("{:#?}", result);

    Ok(())
}

// 'U' of CRUD functions 
async fn update_document(database: &Database) -> Result<(), Box<dyn Error>> {
    let collection = database.collection::<Document>("mycollection");

    let filter = doc! { 
        "name": "Alice"
    };

    let update = doc! { 
        "$set": { "age": 31 }
    };

    collection.update_one(filter, update).await?;

    println!("Document updated!");
 
    Ok(())
}

// 'D' of CRUD functions 
async fn delete_document(database: &Database) -> Result<(), Box<dyn Error>> {
    let collection = database.collection::<Document>("mycollection");

    let filter = doc! { "name": "Alice" };

    collection.delete_one(filter).await?;

    println!("Document deleted!");

    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    //Get command line arguments
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        panic!("Need a command line argument while invoking the program. Use c, r, u, or d for the respective CRUD operation to run.")
    }
    let op = &args[1];

    // Retrieve credentials from Secrets Manager
    let secret_name = "<Your-Seceret-Name>";
    let secret = get_secret(secret_name).await?;

    // Construct connection string using the secret credentials
    let client_uri = format!(
        "mongodb://{}:{}@{}:{}/?replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false",
        secret.username, secret.password, secret.host, secret.port
    );

    // Parse MongoDB client options
    let mut client_options = ClientOptions::parse(&client_uri).await?;
    let ca_file = PathBuf::from(r"/<Path-to-global-bundle>/global-bundle.pem");
    let tls_options = TlsOptions::builder()
        .ca_file_path(ca_file)
        .build();
    client_options.tls = Some(Tls::Enabled(tls_options));

    // Connect to DocumentDB
    let client = Client::with_options(client_options)?;
    let database = client.database("mydatabase");

    // Ping the database to ensure a successful connection
    let _result = database.run_command(doc! { "ping": 1 }).await?;
    println!("Connected to Amazon DocumentDB using credentials from Secrets Manager! Respose: {}", _result);

    //Set of CRUD operations executed based on user input via command line
    match op.as_str() {
        //Create a document
        "C" | "c" => create_document(&database).await?,
        //Read a document
        "R" | "r" => read_document(&database).await?,
        //Update a document
        "U" | "u" => update_document(&database).await?,
        //Delete a document
        "D" | "d" => delete_document(&database).await?,
        _ => println!("Invalid input argument {}. Use c, r, u, or d for the respective CRUD operation to run.", op),
    }

    Ok(())
}
