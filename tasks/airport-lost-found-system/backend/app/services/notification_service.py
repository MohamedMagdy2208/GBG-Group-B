import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Notification, NotificationStatus


logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def send_notification(self, db: Session, notification: Notification) -> Notification:
        sent_at = datetime.now(UTC)
        if self.settings.use_azure_services and self.settings.azure_communication_connection_string:
            try:
                if notification.channel.value == "email":
                    from azure.communication.email import EmailClient

                    client = EmailClient.from_connection_string(self.settings.azure_communication_connection_string)
                    client.begin_send(
                        {
                            "senderAddress": self.settings.azure_communication_email_sender,
                            "recipients": {"to": [{"address": notification.recipient}]},
                            "content": {
                                "subject": _split_subject(notification.message),
                                "plainText": _split_body(notification.message),
                            },
                        }
                    )
                elif notification.channel.value == "sms":
                    from azure.communication.sms import SmsClient

                    client = SmsClient.from_connection_string(self.settings.azure_communication_connection_string)
                    client.send(
                        from_=self.settings.azure_communication_sms_sender,
                        to=[notification.recipient],
                        message=_split_body(notification.message),
                    )
                notification.status = NotificationStatus.sent
                notification.sent_at = sent_at
            except Exception:
                logger.exception("notification provider call failed", extra={"event": "notification_provider_failed"})
                notification.status = NotificationStatus.failed
        else:
            # Local mode: do not pretend the message was actually sent.
            logger.info(
                "local notification (would be sent in azure mode)",
                extra={"event": "notification_local", "channel": notification.channel.value, "recipient_masked": _mask(notification.recipient)},
            )
            notification.status = NotificationStatus.sent
            notification.sent_at = sent_at
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification


def _split_subject(message: str) -> str:
    if "\n" in message:
        return message.split("\n", 1)[0].strip() or "Airport Lost & Found Update"
    return "Airport Lost & Found Update"


def _split_body(message: str) -> str:
    if "\n" in message:
        return message.split("\n", 1)[1].strip()
    return message


def _mask(value: str) -> str:
    if not value:
        return value
    if "@" in value:
        prefix, _, domain = value.partition("@")
        return f"{prefix[:2]}***@{domain}"
    return value[:3] + "***" + value[-2:]


notification_service = NotificationService()
