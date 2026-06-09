import json
import uuid
from datetime import datetime, timezone

import pika

from app.core.config import settings


class RabbitMQClient:
    """
    Publica eventos de domínio no RabbitMQ.
    Envelope segue o contrato do async-docs.yaml (EventEnvelopeBase).
    """

    EXCHANGE = "domain.events"

    def _get_channel(self):
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_USER,
            settings.RABBITMQ_PASSWORD,
        )
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                credentials=credentials,
                connection_attempts=2,
                retry_delay=1,
            )
        )
        return connection, connection.channel()

    def _build_envelope(self, event_type: str, payload: dict) -> dict:
        """
        Monta o envelope padrão conforme EventEnvelopeBase do async-docs:
        {eventId, eventType, occurredAt, version, payload}
        """
        return {
            "eventId": f"evt_{uuid.uuid4().hex[:12]}",
            "eventType": event_type,
            "occurredAt": datetime.now(timezone.utc).isoformat(),
            "version": "1.0",
            "payload": payload,
        }

    def publish_user_deactivated(self, user_id: str, reason: str) -> None:
        """
        Publica o evento UserDeactivated no exchange 'domain.events'.
        Routing key: users.deactivated
        Payload segue o contrato UserDeactivatedEvent do async-docs.
        """
        event = self._build_envelope(
            event_type="UserDeactivated",
            payload={
                "userId": user_id,
                "reason": reason,
            },
        )
        try:
            connection, channel = self._get_channel()
            channel.basic_publish(
                exchange=self.EXCHANGE,
                routing_key="users.deactivated",
                body=json.dumps(event),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,  # mensagem persistente
                ),
            )
            connection.close()
        except Exception as e:
            # Não bloqueia o fluxo principal se o RabbitMQ estiver offline
            print(f"[RabbitMQ] Falha ao publicar evento UserDeactivated: {e}")
