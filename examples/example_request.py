import asyncio
from typing import Optional

from cantok import AbstractToken
from pydantic import BaseModel

from simple_mediator import (
    Mediator,
    NextRequestCallable,
    PipelineBehavior,
    Request,
    RequestHandler,
)


class User(BaseModel):
    id: int
    name: str
    email: str


# Define the request
class GetUserByIdRequest(Request[User]):
    user_id: int


# Define the handler for this request
class GetUserByIdHandler(RequestHandler[GetUserByIdRequest, User]):
    async def handle(
        self,
        request: GetUserByIdRequest,
        cancellation_token: Optional[AbstractToken] = None,
    ) -> User:
        # In a real application, this would fetch data from a database
        print("Getting user data from database...")
        # For this example, we'll just return a mock user
        return User(
            id=request.user_id,
            name="John Doe",
            email="johndoe@example.com",
        )


# Define a pipeline behavior (optional)
class LoggingBehavior(PipelineBehavior[GetUserByIdRequest, User]):
    async def handle(
        self,
        request: GetUserByIdRequest,
        next_request: NextRequestCallable[GetUserByIdRequest, User],
        cancellation_token: Optional[AbstractToken] = None,
    ) -> User:
        print(f"Handling request to get user with ID: {request.user_id}")
        if cancellation_token is not None and cancellation_token.is_cancelled():
            cancellation_token.raise_cancelled_exception()
        result = await next_request(request, cancellation_token)
        print(f"Handled request. User data: {result}")
        return result


class AnotherLoggingBehavior(PipelineBehavior[GetUserByIdRequest, User]):
    async def handle(
        self,
        request: GetUserByIdRequest,
        next_request: NextRequestCallable[GetUserByIdRequest, User],
        cancellation_token: Optional[AbstractToken] = None,
    ) -> User:
        print(f"Handling another request to get user with ID: {request.user_id}")
        if cancellation_token is not None and cancellation_token.is_cancelled():
            cancellation_token.raise_cancelled_exception()
        result = await next_request(request, cancellation_token)
        print(f"Handled another request. User data: {result}")
        return result


# Usage example
async def main():
    mediator = Mediator()

    # Register the handler and behavior
    mediator.register_request_handler(GetUserByIdRequest, GetUserByIdHandler)
    mediator.register_pipeline_behavior(LoggingBehavior)
    mediator.register_pipeline_behavior(AnotherLoggingBehavior)

    # Create and send the request
    request = GetUserByIdRequest(user_id=1)
    result = await mediator.send(request)

    print(f"The result after running all the pipelines is: {result}")


# Run the example

if __name__ == "__main__":
    asyncio.run(main())
