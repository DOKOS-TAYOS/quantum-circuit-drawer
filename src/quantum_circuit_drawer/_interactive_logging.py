"""Shared helpers for persistent interactive logging sessions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ._logging import (
    InteractionSource,
    InteractiveLogSession,
    create_interactive_log_session,
    log_interaction,
)
from .renderers._matplotlib_figure import (
    get_interactive_log_session,
    set_interactive_log_session,
)

if TYPE_CHECKING:
    from matplotlib.figure import Figure, SubFigure


def ensure_interactive_log_session(
    *,
    figure: Figure | SubFigure,
    surface: str,
    logger: logging.Logger,
    state: object | None = None,
    source: InteractionSource | str = InteractionSource.PROGRAMMATIC,
    **fields: object,
) -> InteractiveLogSession:
    """Return one persistent figure session, creating and logging it when needed."""

    session = get_interactive_log_session(figure)
    if session is None:
        session = create_interactive_log_session(surface=surface)
        set_interactive_log_session(figure, session)
        if state is not None and hasattr(state, "log_session"):
            setattr(state, "log_session", session)
        log_interaction(
            logger,
            logging.INFO,
            "interactive.session.started",
            "Started interactive session.",
            session=session,
            source=source,
            **fields,
        )
        return session

    if state is not None and hasattr(state, "log_session"):
        setattr(state, "log_session", session)
    return session
