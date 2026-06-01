import json
import pika

from app.core.config import settings


class RabbitMQClient:

    EXCHANGE = "domain.events"

    def _get_channel(self):
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_USER,
            settings.RABBITMQ_PASSWORD
        )
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
                credentials=credentials
            )
        )
        return connection, connection.channel()

    def publish_user_deactivated(self, user_id: str):
        try:
            connection, channel = self._get_channel()
            channel.basic_publish(
                exchange=self.EXCHANGE,
                routing_key="users.deactivated",
                body=json.dumps({"userId": user_id}),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2  # mensagem persistente
                )
            )
            connection.close()
        except Exception as e:
            # Não bloqueia o fluxo principal se o RabbitMQ estiver offline
            print(f"[RabbitMQ] Falha ao publicar evento: {e}")