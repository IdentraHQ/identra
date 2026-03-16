"""
Identra gRPC Health Servicer
Implements health check for tunnel-gateway.
"""
import logging

import grpc
from generated import health_pb2, health_pb2_grpc

logger = logging.getLogger("grpc_health_servicer")


class HealthServicer(health_pb2_grpc.HealthServicer):
    """Health check servicer for tunnel-gateway monitoring."""

    def __init__(self):
        self._status = {}
        logger.info("✅ gRPC HealthServicer initialized")

    def Check(self, request, context):
        """Check if service is alive."""
        service = request.service
        status = self._status.get(
            service,
            health_pb2.HealthCheckResponse.SERVING
        )
        logger.info(f"Health check: {service} → {status}")
        return health_pb2.HealthCheckResponse(status=status)

    def Watch(self, request, context):
        """Stream health status changes."""
        service = request.service
        status = self._status.get(
            service,
            health_pb2.HealthCheckResponse.SERVING
        )
        yield health_pb2.HealthCheckResponse(status=status)

    def set_status(self, service: str, status):
        """Update service health status."""
        self._status[service] = status
        logger.info(f"Health status updated: {service} → {status}")
