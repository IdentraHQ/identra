// Test script to verify tunnel-gateway ← → vault-daemon IPC connection
// Run with: node test-grpc.js

const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');

const PROTO_PATH = '../../libs/identra-proto/proto/vault.proto';

const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true
});

const vaultProto = grpc.loadPackageDefinition(packageDefinition).identra.vault;

const client = new vaultProto.VaultService('[::1]:50051', grpc.credentials.createInsecure());

// Test 1: Store a key
console.log('📤 Test 1: Storing key...');
client.StoreKey({
    key_id: 'test-identity@identra.local',
    key_data: Buffer.from('my-secret-api-key-12345'),
    metadata: {}
}, (err, response) => {
    if (err) {
        console.error('❌ Store failed:', err.message);
        return;
    }
    console.log('✅ Store response:', response);
    
    // Test 2: Check if key exists
    console.log('\n🔍 Test 2: Checking if key exists...');
    client.KeyExists({
        key_id: 'test-identity@identra.local'
    }, (err, response) => {
        if (err) {
            console.error('❌ Exists check failed:', err.message);
            return;
        }
        console.log('✅ Key exists:', response.exists);
        
        // Test 3: Retrieve the key
        console.log('\n📥 Test 3: Retrieving key...');
        client.RetrieveKey({
            key_id: 'test-identity@identra.local'
        }, (err, response) => {
            if (err) {
                console.error('❌ Retrieve failed:', err.message);
                return;
            }
            console.log('✅ Retrieved key data:', response.key_data.toString());
            
            // Test 4: Delete the key
            console.log('\n🗑️  Test 4: Deleting key...');
            client.DeleteKey({
                key_id: 'test-identity@identra.local'
            }, (err, response) => {
                if (err) {
                    console.error('❌ Delete failed:', err.message);
                    return;
                }
                console.log('✅ Delete response:', response);
                
                console.log('\n🎉 All tests passed! IPC integration working.');
                process.exit(0);
            });
        });
    });
});
