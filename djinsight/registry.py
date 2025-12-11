from typing import Dict, Type, Union

from djinsight.providers.base import AsyncBaseProvider, BaseProvider


class ProviderRegistry:
    """
    Registry for djinsight providers.
    Supports both sync and async providers based on settings.
    """

    _providers: Dict[str, Type[BaseProvider]] = {}
    _async_providers: Dict[str, Type[AsyncBaseProvider]] = {}
    _default_provider: str = None

    @classmethod
    def register(
        cls,
        name: str,
        provider_class: Type[BaseProvider],
        async_class: Type[AsyncBaseProvider] = None,
    ):
        """Register a provider with optional async variant."""
        cls._providers[name] = provider_class
        if async_class:
            cls._async_providers[name] = async_class

    @classmethod
    def get_provider(
        cls, name: str = None, use_async: bool = False
    ) -> Union[BaseProvider, AsyncBaseProvider]:
        """
        Get a provider instance.

        Args:
            name: Provider name (optional, uses default if not specified)
            use_async: If True, returns async provider variant
        """
        from djinsight.conf import djinsight_settings

        if name:
            if use_async and name in cls._async_providers:
                return cls._async_providers[name]()
            provider_class = cls._providers.get(name)
        elif cls._default_provider:
            if use_async and cls._default_provider in cls._async_providers:
                return cls._async_providers[cls._default_provider]()
            provider_class = cls._providers.get(cls._default_provider)
        else:
            if djinsight_settings.USE_REDIS:
                if use_async:
                    from djinsight.providers.redis import AsyncRedisProvider

                    return AsyncRedisProvider()
                from djinsight.providers.redis import RedisProvider

                provider_class = RedisProvider
            else:
                if use_async:
                    from djinsight.providers.database import AsyncDatabaseProvider

                    return AsyncDatabaseProvider()
                from djinsight.providers.database import DatabaseProvider

                provider_class = DatabaseProvider

        if not provider_class:
            provider_class = djinsight_settings.get_provider_class()

        return provider_class()

    @classmethod
    def get_async_provider(cls, name: str = None) -> AsyncBaseProvider:
        """Convenience method to get async provider."""
        return cls.get_provider(name=name, use_async=True)

    @classmethod
    def set_default(cls, name: str):
        cls._default_provider = name

    @classmethod
    def list_providers(cls) -> list:
        return list(cls._providers.keys())
