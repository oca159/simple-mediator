import asyncio
from typing import Optional

from simple_mediator import AbstractToken, Mediator, Notification, NotificationHandler


# Define the notification
class UserCreatedNotification(Notification):
    user_id: int
    username: str
    email: str


# Define handlers for this notification
class EmailNotificationHandler(NotificationHandler[UserCreatedNotification]):
    async def handle(
        self,
        notification: UserCreatedNotification,
        cancellation_token: Optional[AbstractToken] = None,
    ) -> None:
        print(f"Sending welcome email to {notification.email}")
        # In a real application, this would send an actual email


class AnalyticsNotificationHandler(NotificationHandler[UserCreatedNotification]):
    async def handle(
        self,
        notification: UserCreatedNotification,
        cancellation_token: Optional[AbstractToken] = None,
    ) -> None:
        print(f"Logging new user creation: User ID {notification.user_id}")
        # In a real application, this might log to an analytics service


class AdminNotificationHandler(NotificationHandler[UserCreatedNotification]):
    async def handle(
        self,
        notification: UserCreatedNotification,
        cancellation_token: Optional[AbstractToken] = None,
    ) -> None:
        print(f"Notifying admin: New user {notification.username} created")
        # In a real application, this might send a notification to an admin panel


# Example usage
async def create_user(mediator: Mediator, user_data: dict) -> None:
    # Simulate user creation
    user_id = 123  # In a real app, this would be generated or returned from a database

    # Create and publish the notification
    notification = UserCreatedNotification(
        user_id=user_id, username=user_data["username"], email=user_data["email"]
    )

    await mediator.publish(notification)


async def main():
    mediator = Mediator()

    # Register the notification handlers
    mediator.register_notification_handler(
        UserCreatedNotification, EmailNotificationHandler
    )
    mediator.register_notification_handler(
        UserCreatedNotification, AnalyticsNotificationHandler
    )
    mediator.register_notification_handler(
        UserCreatedNotification, AdminNotificationHandler
    )

    # Simulate user creation and notification
    user_data = {"username": "new_user", "email": "new_user@example.com"}

    await create_user(mediator, user_data)


# Run the example

if __name__ == "__main__":
    asyncio.run(main())
