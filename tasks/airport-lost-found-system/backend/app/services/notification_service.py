from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Notification, NotificationStatus


class NotificationService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def send_notification(self, db: Session, notification: Notification) -> Notification:
        if self.settings.use_azure_services and self.settings.azure_communication_connection_string:
            if notification.channel.value == "email":
                from azure.communication.email import EmailClient

                client = EmailClient.from_connection_string(self.settings.azure_communication_connection_string)
                client.begin_send(
                    {
                        "senderAddress": self.settings.azure_communication_email_sender,
                        "recipients": {"to": [{"address": notification.recipient}]},
                        "content": {"subject": "Airport Lost & Found Update", "plainText": notification.message},
                    }
                )
            elif notification.channel.value == "sms":
                from azure.communication.sms import SmsClient

                client = SmsClient.from_connection_string(self.settings.azure_communication_connection_string)
                client.send(from_=self.settings.azure_communication_sms_sender, to=[notification.recipient], message=notification.message)
        notification.status = NotificationStatus.sent
        notification.sent_at = datetime.now(UTC)
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification


notification_service = NotificationService()
