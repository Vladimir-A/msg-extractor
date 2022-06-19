import logging

from .message_signed_base import MessageSignedBase


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class MessageSigned(MessageSignedBase):
    """
    Parser for Signed Microsoft Outlook message files.
    """

    def __init__(self, path, **kwargs):
        super().__init__(path, **kwargs)
