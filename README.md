# Simple Mediator

Simple Mediator is a lightweight implementation of the Mediator pattern for Python, inspired by the MediatR library. It provides a way to decouple the sending of messages from their handling, supporting requests, notifications, and pipeline behaviors.

## Installation

You can install Simple Mediator using pip or uv:

```bash
pip install simple-mediator

# or using uv

uv add simple-mediator
```

## Usage

### Requests

In the Mediator pattern, a request represents a command or query that you want to execute. It encapsulates all the data needed to perform a specific operation. Requests are typically used for operations that return a result.

Key characteristics of requests:

- They are immutable data structures.
- Each request type corresponds to a single operation.
- They usually expect a response.

##### The Request interface

The `Request` interface defines the contract for creating custom requests, it looks like this:

```python
class Request(BaseModel, Generic[TResponse]):
    pass
```

Key points about this interface:

- It inherits from Pydantic's BaseModel, allowing for easy data validation and serialization.
- It's generic, with TResponse representing the expected response type.
- It's an empty base class, serving as a marker for request types.

##### Implementing a Request

```python
from simple_mediator import Request


class User(BaseModel):
  id: int
  name: str
  email: str


class GetUserRequest(Request[User]):
    user_id: int

```

In this example:

`GetUserRequest` is a request that expects a User object as a response.
It has one field, user_id, which is required to fetch the user.

##### The RequestHandler interface

For each request, you need a corresponding handler. The `RequestHandler` interface is defined as:

```python
class RequestHandler(ABC, Generic[TRequest, TResponse]):
    @abstractmethod
    async def handle(
        self, request: TRequest, cancellation_token: Optional[AbstractToken] = None
    ) -> TResponse:
        pass
```

Key points:

- It's generic, allowing you to specify the request and response types.
- The handle method is where you implement the logic to process the request.
- It receives the request and an optional cancellation token.
- It should return the response of the type specified in TResponse.

##### Implementing a RequestHandler

Here's an example of implementing a handler for the `GetUserRequest`:

```python
class GetUserHandler(RequestHandler[GetUserRequest, User]):
    async def handle(
        self, request: GetUserRequest, cancellation_token: Optional[AbstractToken] = None
    ) -> User:
        # In a real application, you would fetch this from a database
        if request.user_id == 1:
            return User(id=1, name="John Doe", email="john@example.com")
        else:
            raise ValueError("User not found")
```

##### Registering and using requests

To use requests with the Mediator:

```python
mediator = Mediator()
mediator.register_request_handler(GetUserRequest, GetUserHandler)
```

##### Sending a request

```python
async def get_user(user_id: int) -> User:
    request = GetUserRequest(user_id=user_id)
    return await mediator.send(request)

# Usage
user = await get_user(1)
print(user)  # User(id=1, name="John Doe", email="john@example.com")
```

### Notifications

In the Mediator pattern, a notification represents an event that has occurred in your system. Unlike requests, notifications are used for scenarios where you want to inform multiple handlers about an event without expecting a specific response.

Key characteristics of notifications:

- They represent events that have already occurred.
- Multiple handlers can respond to a single notification.
- They don't expect a return value.

##### The Notification interface

The `Notification` interface defines the contract for creating custom notifications, it looks like this:

```python
class Notification(BaseModel):
    pass
```

Key points about this interface:

- It inherits from Pydantic's BaseModel, allowing for easy data validation and serialization.
- It's a simple base class, serving as a marker for notification types.

##### Implementing a Notification

To create a specific notification, you subclass the Notification class and define the necessary fields:

```python
class UserCreatedNotification(Notification):
    user_id: int
    username: str
    email: str
```

In this example:

- UserCreatedNotification represents an event where a new user has been created.
- It contains relevant information about the created user.

##### The NotificationHandler interface

For each notification, you can have multiple handlers. The NotificationHandler interface is defined as:

```python
class NotificationHandler(ABC, Generic[T]):
    @abstractmethod
    async def handle(
        self, notification: T, cancellation_token: Optional[AbstractToken] = None
    ) -> None:
        pass
```

Key points:

- It's generic, allowing you to specify the notification type.
- The handle method is where you implement the logic to process the notification.
- It receives the notification and an optional cancellation token.
- It doesn't return a value (returns None).

##### Implementing a NotificationHandler

Here's an example of implementing handlers for the UserCreatedNotification:

```python
class EmailNotificationHandler(NotificationHandler[UserCreatedNotification]):
    async def handle(
        self, notification: UserCreatedNotification, cancellation_token: Optional[AbstractToken] = None
    ) -> None:
        print(f"Sending welcome email to {notification.email}")
        # In a real application, you would send an actual email here

class AnalyticsNotificationHandler(NotificationHandler[UserCreatedNotification]):
    async def handle(
        self, notification: UserCreatedNotification, cancellation_token: Optional[AbstractToken] = None
    ) -> None:
        print(f"Logging new user creation: User ID {notification.user_id}")
        # In a real application, you might log this to an analytics service
```

##### Registering and using notifications

To use notifications with the Mediator:

```python
mediator = Mediator()
mediator.register_notification_handler(UserCreatedNotification, EmailNotificationHandler)
mediator.register_notification_handler(UserCreatedNotification, AnalyticsNotificationHandler)
```

##### Publish a notification

```python
async def create_user(username: str, email: str) -> None:
    # Logic to create user in database
    user_id = 123  # Assume this is returned from database
    notification = UserCreatedNotification(user_id=user_id, username=username, email=email)
    await mediator.publish(notification)

# Usage
await create_user("johndoe", "john@example.com")
```

##### Benefits of using notifications

- Decoupling: The code that triggers an event is decoupled from the code that handles its effects.
- Extensibility: You can easily add new handlers for existing notifications without modifying existing code.
- Single Responsibility: Each handler can focus on a specific task in response to an event.
- Scalability: Handlers can be executed asynchronously, allowing for better performance in high-load scenarios.

##### Best practices for notifications

- Use past tense: Name notifications to represent events that have already occurred (e.g., `UserCreatedNotification`, `OrderShippedNotification`).
- Include relevant data: Ensure the notification contains all necessary information for handlers to process the event.
- Keep handlers focused: Each handler should perform a single, specific task in response to a notification.
- Consider idempotency: Design handlers to be idempotent, as notifications might be delivered more than once in some scenarios.
- Use for side effects: Notifications are great for triggering side effects like sending emails, updating caches, or logging.

##### Notifications vs Requests

- Use notifications when you want to inform multiple parts of your system about an event without expecting a specific response.
- Use requests when you need to perform a specific operation and expect a result.

### Pipeline behaviors

A pipeline in the context of the Mediator pattern is a series of operations that are executed in a specific order when processing a request. The pipeline allows you to add cross-cutting concerns or additional processing steps before and after the actual request handler is invoked.

The main benefits of using a pipeline are:

- Separation of concerns: You can extract common logic from your request handlers.
- Reusability: Pipeline behaviors can be applied to multiple request types.
- Flexibility: You can easily add, remove, or reorder pipeline steps without modifying the request handlers.

##### The PipelineBehavior interface

The `PipelineBehavior` interface defines the contract for creating custom pipeline steps. In your implementation, it looks like this:

```python
class PipelineBehavior(ABC, Generic[TRequest, TResponse]):
    @abstractmethod
    async def handle(
        self,
        request: TRequest,
        next_request: NextRequestCallable[TRequest, TResponse],
        cancellation_token: Optional[AbstractToken] = None,
    ) -> TResponse:
        pass
```

Key points about this interface:

- It's generic, allowing you to specify the request and response types.
- The handle method is where you implement the behavior's logic.
- It receives the current request, a next_request callable to invoke the next step in the pipeline, and an optional cancellation token.
- It should return the response of the same type as specified in the generic parameter.

##### How Pipeline Behaviors Work

When you register pipeline behaviors with the Mediator, they are wrapped around the request handler in the order they are registered. Each behavior has the opportunity to:

- Perform actions before the request is handled (pre-processing)
- Modify the request
- Call the next step in the pipeline
- Perform actions after the request is handled (post-processing)
- Modify the response
- Handle exceptions
- Here's a conceptual view of how the pipeline works:

```
[Behavior 1] -> [Behavior 2] -> [Behavior 3] -> [Request Handler] -> [Behavior 3] -> [Behavior 2] -> [Behavior 1]
```

The request flows from left to right, and then the response flows back from right to left.

##### Implementing a Pipeline Behavior

```python
from cantok import AbstractToken
from simple_mediator import PipelineBehavior, NextRequestCallable


class LoggingBehavior(PipelineBehavior[GetUserRequest, User]):
    async def handle(
        self,
        request: TRequest,
        next_request: NextRequestCallable[GetUserRequest, User],
        cancellation_token: Optional[AbstractToken] = None,
    ) -> TResponse:
        print(f"Handling request: {request}")
        try:
            response = await next_request(request, cancellation_token)
            print(f"Request handled successfully: {response}")
            return response
        except Exception as e:
            print(f"Error handling request: {e}")
            raise
```

This behavior logs the request, calls the next step in the pipeline, logs the response or any error, and then returns the response or re-raises the exception.

##### Using pipeline behaviors

```python
mediator = Mediator()
mediator.register_pipeline_behavior(LoggingBehavior)
mediator.register_pipeline_behavior(ValidationBehavior)
mediator.register_pipeline_behavior(CachingBehavior)
```

### Cancellation tokens

Simple Mediator supports cancellation tokens using the `cantok` library:

It supports all the cancellation tokens provided by `cantok`, such as `SimpleToken`, `TimeoutToken`, `ConditionToken` or `CounterToken`.
More information about tokens here: [cantok](https://cantok.readthedocs.io/en/latest/what_are_tokens/in_general/)

```python
import asyncio
from cantok import SimpleToken


async def main():
    token = SimpleToken()
    request = GetUserRequest(user_id=1)

    # In another coroutine or thread:
    # token.cancel()

    try:
        result = await mediator.send(request, cancellation_token=token)
    except Exception as e:
        print(f"Request was cancelled: {e}")

asyncio.run(main())
```

### Examples

You can find examples of how to use the mediator in the [examples](https://github.com/oca159/simple-mediator/tree/main/examples) directory.

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### License

This project is licensed under the GPL License.
