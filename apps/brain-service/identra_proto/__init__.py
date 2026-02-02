"""
Identra Proto - Generated gRPC Python Stubs
Generated from libs/identra-proto/proto/*.proto files

This package contains the generated Python gRPC stubs for:
- auth: Authentication service
- health: Health check service  
- memory: Memory storage and retrieval service
- vault: Vault operations service
"""

# Import the main memory service components for easy access
from .proto.memory_pb2 import (
    Memory,
    MemoryMatch, 
    StoreMemoryRequest,
    StoreMemoryResponse,
    QueryMemoriesRequest, 
    QueryMemoriesResponse,
    SearchMemoriesRequest,
    SearchMemoriesResponse,
    GetRecentMemoriesRequest,
    GetRecentMemoriesResponse,
    GetMemoryRequest,
    GetMemoryResponse,
    DeleteMemoryRequest,
    DeleteMemoryResponse
)

from .proto.memory_pb2_grpc import (
    MemoryServiceStub,
    MemoryServiceServicer
)

__all__ = [
    # Memory messages
    "Memory",
    "MemoryMatch",
    "StoreMemoryRequest", 
    "StoreMemoryResponse",
    "QueryMemoriesRequest",
    "QueryMemoriesResponse", 
    "SearchMemoriesRequest",
    "SearchMemoriesResponse",
    "GetRecentMemoriesRequest",
    "GetRecentMemoriesResponse",
    "GetMemoryRequest",
    "GetMemoryResponse",
    "DeleteMemoryRequest",
    "DeleteMemoryResponse",
    
    # gRPC service stubs
    "MemoryServiceStub",
    "MemoryServiceServicer"
]