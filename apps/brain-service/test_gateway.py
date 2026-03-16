import sys
import os

# Tell Python to look inside the 'generated' folder
sys.path.append(os.path.join(os.path.dirname(__file__), 'generated'))

import grpc
import memory_pb2
import memory_pb2_grpc

def test_connection():
    # Connect to the Gateway using the IPv6 address
    channel = grpc.insecure_channel('[::1]:50051')
    client = memory_pb2_grpc.MemoryServiceStub(channel)
    
    print("⏳ Sending memory to Gateway...")
    
    try:
        response = client.StoreMemory(
            memory_pb2.StoreMemoryRequest(
                content="Hello from the Brain Service! This is a test memory.",
                metadata={"test": "true", "developer": "sailesh"},
                tags=["test-run"]
            )
        )
        print(f"✅ Success! Memory saved with ID: {response.memory_id}")
    except grpc.RpcError as e:
        print(f"❌ Connection Failed!")
        print(f"Details: {e.details()}")

if __name__ == "__main__":
    test_connection()