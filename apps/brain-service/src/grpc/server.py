"""
Identra gRPC Server
"""
import os
import logging
from concurrent import futures
import grpc

from generated import health_pb2_grpc, memory_pb2_grpc
from src.grpc.memory_servicer import MemoryServicer
from src.grpc.health_servicer import HealthServicer

logger = logging.getLogger("grpc_server")
GRPC_PORT = int(os.getenv("GRPC_PORT", "50051"))

class GRPCServer:
    def __init__(self, conversation_store, embedding_service=None):
        self.conversation_store = conversation_store
        self.embedding_service = embedding_service
        self.server = None

    def start(self):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        memory_pb2_grpc.add_MemoryServiceServicer_to_server(MemoryServicer(self.conversation_store, embedding_service=self.embedding_service), self.server)
        health_pb2_grpc.add_HealthServicer_to_server(HealthServicer(), self.server)
        self.server.add_insecure_port(f"[::]:{GRPC_PORT}")
        self.server.start()
        logger.info(f"✅ gRPC server started on port {GRPC_PORT}")
        return self.server

    def stop(self):
        if self.server:
            self.server.stop(grace=5)
            logger.info("🛑 gRPC server stopped")
