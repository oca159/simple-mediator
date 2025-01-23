from abc import ABC, abstractmethod
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
)

from cantok import AbstractToken
from pydantic import BaseModel

T = TypeVar("T")
TRequest = TypeVar("TRequest", bound="Request")
TResponse = TypeVar("TResponse")

NextRequestCallable = Callable[
    [TRequest, Optional[AbstractToken]], Coroutine[Any, Any, TResponse]
]


class Request(BaseModel, Generic[TResponse]):
    """
    Base class for all requests. Inherits from Pydantic's BaseModel for data validation.
    Generic over the expected response type.
    """

    pass


class Notification(BaseModel):
    """
    Base class for all notifications. Inherits from Pydantic's BaseModel for data validation.
    """

    pass


class RequestHandler(ABC, Generic[TRequest, TResponse]):
    """
    Abstract base class for request handlers. Generic over the request and response types.
    """

    @abstractmethod
    async def handle(
        self, request: TRequest, cancellation_token: Optional[AbstractToken] = None
    ) -> TResponse:
        """
        Handle the given request.

        Args:
            request (TRequest): The request to handle.
            cancellation_token (Optional[AbstractToken]): Token for cancelling the operation.

        Returns:
            TResponse: The response to the request.
        """
        pass


class NotificationHandler(ABC, Generic[T]):
    """
    Abstract base class for notification handlers. Generic over the notification type.
    """

    @abstractmethod
    async def handle(
        self, notification: T, cancellation_token: Optional[AbstractToken] = None
    ) -> None:
        """
        Handle the given notification.

        Args:
            notification (T): The notification to handle.
            cancellation_token (Optional[AbstractToken]): Token for cancelling the operation.
        """
        pass


class PipelineBehavior(ABC, Generic[TRequest, TResponse]):
    """
    Abstract base class for pipeline behaviors. Generic over the request and response types.
    """

    @abstractmethod
    async def handle(
        self,
        request: TRequest,
        next_request: NextRequestCallable[TRequest, TResponse],
        cancellation_token: Optional[AbstractToken] = None,
    ) -> TResponse:
        """
        Handle the request and call the next behavior in the pipeline.

        Args:
            request (TRequest): The request to handle.
            next_request (NextRequestCallable[TRequest, TResponse]): The next behavior in the pipeline.
            cancellation_token (Optional[AbstractToken]): Token for cancelling the operation.

        Returns:
            TResponse: The response from the pipeline.
        """
        pass


class Mediator:
    """
    Mediator class that coordinates the sending of requests with pipeline behaviors and publishing of notifications
    in a mediator pattern implementation.

    Args:
        request_handlers (Optional[Dict[Type[Request], Type[RequestHandler]]]): A dictionary
            mapping Request types to their corresponding RequestHandler types. Defaults to None.
        notification_handlers (Optional[Dict[Type[Notification], List[Type[NotificationHandler]]]]):
            A dictionary mapping Notification types to their corresponding list of NotificationHandler
            types. Defaults to None.
        pipeline_behaviors (Optional[List[Type[PipelineBehavior]]]): A list of PipelineBehavior
            types that will be applied to requests in the order they are provided. These
            behaviors can modify or enhance the request processing pipeline. Defaults to None.

    Attributes:
        request_handlers (Dict[Type[Request], Type[RequestHandler]]): Stores the mapping of
            request types to their handlers.
        notification_handlers (Dict[Type[Notification], List[Type[NotificationHandler]]]):
            Stores the mapping of notification types to their handlers.
        pipeline_behaviors (List[Type[PipelineBehavior]]): Stores the list of pipeline
            behaviors to be applied during request processing.
    """

    def __init__(
        self,
        request_handlers: Optional[Dict[Type[Request], Type[RequestHandler]]] = None,
        notification_handlers: Optional[
            Dict[Type[Notification], List[Type[NotificationHandler]]]
        ] = None,
        pipeline_behaviors: Optional[List[Type[PipelineBehavior]]] = None,
    ):
        self.request_handlers: Dict[Type[Request], Type[RequestHandler]] = (
            request_handlers or {}
        )
        self.notification_handlers: Dict[
            Type[Notification], List[Type[NotificationHandler]]
        ] = notification_handlers or {}
        self.pipeline_behaviors: List[Type[PipelineBehavior]] = pipeline_behaviors or []

    def register_request_handler(
        self, request_type: Type[Request], handler_type: Type[RequestHandler]
    ) -> None:
        """
        Register a request handler for a specific request type.

        Args:
            request_type (Type[Request]): The type of request.
            handler_type (Type[RequestHandler]): The type of handler for the request.
        """
        self.request_handlers[request_type] = handler_type

    def register_notification_handler(
        self,
        notification_type: Type[Notification],
        handler_type: Type[NotificationHandler],
    ) -> None:
        """
        Register a notification handler for a specific notification type.

        Args:
            notification_type (Type[Notification]): The type of notification.
            handler_type (Type[NotificationHandler]): The type of handler for the notification.
        """
        self.notification_handlers.setdefault(notification_type, []).append(
            handler_type
        )

    def register_pipeline_behavior(self, behavior_type: Type[PipelineBehavior]) -> None:
        """
        Register a pipeline behavior.

        Args:
            behavior_type (Type[PipelineBehavior]): The type of pipeline behavior to register.
        """
        self.pipeline_behaviors.append(behavior_type)

    async def send(
        self,
        request: Request[TResponse],
        cancellation_token: Optional[AbstractToken] = None,
    ) -> TResponse:
        """
        Send a request through the mediator.

        Args:
            request (Request[TResponse]): The request to send.
            cancellation_token (Optional[AbstractToken]): Token for cancelling the operation.

        Returns:
            TResponse: The response from handling the request.

        Raises:
            ValueError: If no handler is registered for the request type.
        """
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
        self, handler: RequestHandler[Request, TResponse]
    ) -> NextRequestCallable[TRequest, TResponse]:
        """
        Create the pipeline of behaviors wrapped around the request handler.

        Args:
            handler (RequestHandler[TRequest, TResponse]): The core request handler.

        Returns:
            NextRequestCallable[TRequest, TResponse]: The pipeline function that will process the request.
        """
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
        """
        Publish a notification to all registered handlers.

        Args:
            notification (Notification): The notification to publish.
            cancellation_token (Optional[AbstractToken]): Token for cancelling the operation.
        """
        notification_type = type(notification)
        handlers = [
            handler_type()
            for handler_type in self.notification_handlers.get(notification_type, [])
        ]

        for handler in handlers:
            self._check_cancellation_token(cancellation_token)
            await handler.handle(notification, cancellation_token)

    async def __aenter__(self):
        """
        Async context manager enter method.

        Returns:
            Mediator: The mediator instance.
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit method.
        """
        pass

    @staticmethod
    def _check_cancellation_token(
        cancellation_token: Optional[AbstractToken] = None,
    ) -> None:
        """
        Check if the cancellation token has been cancelled and raise an exception if so.

        Args:
            cancellation_token (Optional[AbstractToken]): The cancellation token to check.

        Raises:
            Exception: If the cancellation token has been cancelled.
        """
        if cancellation_token is not None and cancellation_token.cancelled:
            cancellation_token.raise_cancelled_exception()


__all__ = [
    "Request",
    "Notification",
    "RequestHandler",
    "NotificationHandler",
    "PipelineBehavior",
    "Mediator",
    "T",
    "TRequest",
    "TResponse",
    "AbstractToken",
]
