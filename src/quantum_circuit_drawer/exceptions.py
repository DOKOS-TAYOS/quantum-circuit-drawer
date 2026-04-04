"""Project-specific exceptions."""


class QuantumCircuitDrawerError(Exception):
    """Base exception for the library."""


class UnsupportedFrameworkError(QuantumCircuitDrawerError):
    """Raised when a framework or circuit object cannot be adapted."""


class UnsupportedBackendError(QuantumCircuitDrawerError):
    """Raised when a renderer backend is not available."""


class UnsupportedOperationError(QuantumCircuitDrawerError):
    """Raised when a circuit operation cannot be represented meaningfully."""


class LayoutError(QuantumCircuitDrawerError):
    """Raised when layout computation fails."""


class StyleValidationError(QuantumCircuitDrawerError):
    """Raised when draw style options are invalid."""


class RenderingError(QuantumCircuitDrawerError):
    """Raised when a rendered circuit cannot be written to the requested output."""
