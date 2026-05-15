"""Project-specific exceptions."""


class QuantumCircuitDrawerError(Exception):
    """Base exception for errors raised intentionally by the library.

    Raised when:
        Catch this class when you want one handler for adapter, layout, style,
        rendering, and unsupported-feature errors produced by ``quantum_circuit_drawer``.
    """


class UnsupportedFrameworkError(QuantumCircuitDrawerError):
    """Raised when a framework or circuit object cannot be adapted.

    Raised when:
        The input object is not recognized, the requested ``framework=...`` does not
        match the object, or an optional framework dependency is missing.
    """


class UnsupportedBackendError(QuantumCircuitDrawerError):
    """Raised when a renderer backend is not available.

    Raised when:
        A public config requests a backend other than the supported Matplotlib renderer.
        The current accepted backend value is ``"matplotlib"``.
    """


class UnsupportedOperationError(QuantumCircuitDrawerError):
    """Raised when a circuit operation cannot be represented meaningfully.

    Raised when:
        A supported framework contains an operation outside the drawable subset and the
        active unsupported-operation policy is ``"raise"``.
    """


class LayoutError(QuantumCircuitDrawerError):
    """Raised when layout computation fails.

    Raised when:
        The normalized circuit cannot be placed into a valid 2D or 3D layout, usually
        because the input geometry or topology constraints are inconsistent.
    """


class StyleValidationError(QuantumCircuitDrawerError):
    """Raised when draw style options are invalid.

    Raised when:
        A ``DrawStyle`` or style mapping contains an unknown field, invalid type, or
        non-positive numeric value where a positive size or line width is required.
    """


class RenderingError(QuantumCircuitDrawerError):
    """Raised when rendered output cannot be produced or saved.

    Raised when:
        Matplotlib rendering or figure saving fails after the circuit has already been
        normalized and laid out.
    """
