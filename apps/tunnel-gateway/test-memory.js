// Test script for MemoryService
// Run with: node test-memory.js (requires @grpc/grpc-js and @grpc/proto-loader)

const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const path = require('path');

const PROTO_PATH = path.join(__dirname, '../../libs/identra-proto/proto/memory.proto');

const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true,
    includeDirs: [path.join(__dirname, '../../libs/identra-proto/proto')]
});

const memoryProto = grpc.loadPackageDefinition(packageDefinition).identra.memory;

const client = new memoryProto.MemoryService('[::1]:50051', grpc.credentials.createInsecure());

console.log('🧠 Testing Memory Service...\n');

// Test 1: Store a memory
console.log('📤 Test 1: Storing memory...');
client.StoreMemory({
    content: 'The user prefers dark mode and uses Python for data analysis',
    metadata: {
        category: 'preference',
        importance: 'high'
    },
    tags: ['ui', 'python', 'preference']
}, (err, response) => {
    if (err) {
        console.error('❌ Store failed:', err.message);
        return;
    }
    console.log('✅ Memory stored:', response);
    const memoryId = response.memory_id;
    
    // Test 2: Store another memory
    console.log('\n📤 Test 2: Storing another memory...');
    client.StoreMemory({
        content: 'User works on machine learning projects using TensorFlow',
        metadata: {
            category: 'work',
            importance: 'medium'
        },
        tags: ['ml', 'tensorflow', 'python']
    }, (err, response2) => {
        if (err) {
            console.error('❌ Store failed:', err.message);
            return;
        }
        console.log('✅ Second memory stored:', response2);
        
        // Test 3: Query memories
        console.log('\n🔍 Test 3: Querying memories with "python"...');
        client.QueryMemories({
            query: 'python',
            limit: 10,
            filters: {}
        }, (err, queryResponse) => {
            if (err) {
                console.error('❌ Query failed:', err.message);
                return;
            }
            console.log(`✅ Found ${queryResponse.total_count} memories:`);
            queryResponse.memories.forEach((mem, i) => {
                console.log(`   ${i + 1}. ${mem.content.substring(0, 50)}...`);
            });
            
            // Test 4: Get specific memory
            console.log(`\n📥 Test 4: Getting memory by ID: ${memoryId}...`);
            client.GetMemory({
                memory_id: memoryId
            }, (err, getResponse) => {
                if (err) {
                    console.error('❌ Get failed:', err.message);
                    return;
                }
                console.log('✅ Retrieved memory:', {
                    id: getResponse.memory.id,
                    content: getResponse.memory.content,
                    tags: getResponse.memory.tags
                });
                
                // Test 5: Search with embedding (using dummy embedding)
                console.log('\n🔎 Test 5: Vector search (with dummy embedding)...');
                const dummyEmbedding = new Array(384).fill(0).map(() => Math.random());
                client.SearchMemories({
                    query_embedding: dummyEmbedding,
                    limit: 3,
                    similarity_threshold: 0.0
                }, (err, searchResponse) => {
                    if (err) {
                        console.error('❌ Search failed:', err.message);
                        return;
                    }
                    console.log(`✅ Search found ${searchResponse.matches.length} matches:`);
                    searchResponse.matches.forEach((match, i) => {
                        console.log(`   ${i + 1}. Score: ${match.similarity_score.toFixed(4)} - ${match.memory.content.substring(0, 40)}...`);
                    });
                    
                    // Test 6: Delete memory
                    console.log(`\n🗑️  Test 6: Deleting memory ${memoryId}...`);
                    client.DeleteMemory({
                        memory_id: memoryId
                    }, (err, deleteResponse) => {
                        if (err) {
                            console.error('❌ Delete failed:', err.message);
                            return;
                        }
                        console.log('✅ Delete response:', deleteResponse);
                        
                        console.log('\n🎉 All MemoryService tests passed!');
                        process.exit(0);
                    });
                });
            });
        });
    });
});
