class ConfigurationError(Exception):
    """
    Exception raised for programming errors at application construction time

    This exception indicates incorrect usage of the framework.
    It should be raised before the application has been started.
    """
