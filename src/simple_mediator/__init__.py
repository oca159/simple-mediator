from abc import ABC, abstractmethod
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Generic,
    List,
    Type,
    TypeVar,
    Optional,
)

from cantok import AbstractToken
from pydantic import BaseModel

T = TypeVar("T")
TRequest = TypeVar("TRequest", bound="Request")
TResponse = TypeVar("TResponse")


class Request(BaseModel, Generic[TResponse]):
    pass


class Notification(BaseModel):
    pass


class RequestHandler(ABC, Generic[TRequest, TResponse]):
    @abstractmethod
    async def handle(
        self, request: TRequest, cancellation_token: Optional[AbstractToken] = None
    ) -> TResponse:
        pass


class NotificationHandler(ABC, Generic[T]):
    @abstractmethod
    async def handle(
        self, notification: T, cancellation_token: Optional[AbstractToken] = None
    ) -> None:
        pass


class PipelineBehavior(ABC, Generic[TRequest, TResponse]):
    @abstractmethod
    async def handle(
        self,
        request: TRequest,
        next_request: Callable[
            [TRequest, Optional[AbstractToken]], Coroutine[Any, Any, TResponse]
        ],
        cancellation_token: Optional[AbstractToken] = None,
    ) -> TResponse:
        pass


class Mediator:
    def __init__(self):
        self.request_handlers: Dict[Type[Request], Type[RequestHandler]] = {}
        self.notification_handlers: Dict[
            Type[Notification], List[Type[NotificationHandler]]
        ] = {}
        self.pipeline_behaviors: List[Type[PipelineBehavior]] = []

    def register_request_handler(
        self, request_type: Type[Request], handler_type: Type[RequestHandler]
    ) -> None:
        self.request_handlers[request_type] = handler_type

    def register_notification_handler(
        self,
        notification_type: Type[Notification],
        handler_type: Type[NotificationHandler],
    ) -> None:
        self.notification_handlers.setdefault(notification_type, []).append(
            handler_type
        )

    def register_pipeline_behavior(self, behavior_type: Type[PipelineBehavior]) -> None:
        self.pipeline_behaviors.append(behavior_type)

    async def send(
        self,
        request: Request[TResponse],
        cancellation_token: Optional[AbstractToken] = None,
    ) -> TResponse:
        request_type = type(request)
        if request_type not in self.request_handlers:
            raise ValueError(f"No handler registered for request type {request_type}")

        handler = self.request_handlers[request_type]()

        # Create the pipeline
        pipeline = self._create_pipeline(handler)

        # Execute the pipeline
        self._check_cancellation_token(cancellation_token)
        return await pipeline(request, cancellation_token)

    def _create_pipeline(
        self, handler: RequestHandler[TRequest, TResponse]
    ) -> Callable[[TRequest, Optional[AbstractToken]], Coroutine[Any, Any, TResponse]]:
        # Start with the handler itself
        pipeline = handler.handle

        # Wrap the pipeline with each behavior, in reverse order
        for behavior_type in reversed(self.pipeline_behaviors):
            behavior = behavior_type()
            next_pipeline = pipeline

            async def pipeline_step(
                request: TRequest,
                token: Optional[AbstractToken] = None,
                behavior=behavior,
                next_pipeline=next_pipeline,
            ) -> TResponse:
                return await behavior.handle(request, next_pipeline, token)

            pipeline = pipeline_step

        return pipeline

    async def publish(
        self,
        notification: Notification,
        cancellation_token: Optional[AbstractToken] = None,
    ) -> None:
        notification_type = type(notification)
        handlers = [
            handler_type()
            for handler_type in self.notification_handlers.get(notification_type, [])
        ]

        for handler in handlers:
            self._check_cancellation_token(cancellation_token)
            await handler.handle(notification, cancellation_token)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @staticmethod
    def _check_cancellation_token(
        cancellation_token: Optional[AbstractToken] = None,
    ) -> None:
        if cancellation_token is not None and cancellation_token.cancelled:
            cancellation_token.raise_cancelled_exception()
