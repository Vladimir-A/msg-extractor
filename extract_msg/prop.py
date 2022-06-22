import datetime
import logging

import olefile

from . import constants
from .enum import ErrorCode, ErrorCodeType
from .utils import fromTimeStamp, filetimeToUtc, properHex


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def createProp(string):
    temp = constants.ST2.unpack(string)[0]
    if temp in constants.FIXED_LENGTH_PROPS:
        return FixedLengthProp(string)
    else:
        if temp not in constants.VARIABLE_LENGTH_PROPS:
            # DEBUG
            logger.warning(f'Unknown property type: {properHex(temp)}')
        return VariableLengthProp(string)


class PropBase:
    """
    Base class for Prop instances.
    """

    def __init__(self, string):
        self.__raw = string
        self.__name = properHex(string[3::-1]).upper()
        self.__type, self.__flags = constants.ST2.unpack(string)
        self.__fm = self.__flags & 1 == 1
        self.__fr = self.__flags & 2 == 2
        self.__fw = self.__flags & 4 == 4

    @property
    def flagMandatory(self):
        """
        Boolean, is the "mandatory" flag set?
        """
        return self.__fm

    @property
    def flagReadable(self):
        """
        Boolean, is the "readable" flag set?
        """
        return self.__fr

    @property
    def flagWritable(self):
        """
        Boolean, is the "writable" flag set?
        """
        return self.__fw

    @property
    def flags(self):
        """
        Integer that contains property flags.
        """
        return self.__flags

    @property
    def name(self):
        """
        Property "name".
        """
        return self.__name

    @property
    def raw(self):
        """
        Raw binary string that defined the property.
        """
        return self.__raw

    @property
    def type(self):
        """
        The type of property.
        """
        return self.__type


class FixedLengthProp(PropBase):
    """
    Class to contain the data for a single fixed length property.

    Currently a work in progress.
    """

    def __init__(self, string):
        super().__init__(string)
        self.__value = self.parseType(self.type, constants.STFIX.unpack(string)[0])

    def parseType(self, _type, stream) -> Any:
        """
        Converts the data in :param stream: to a much more accurate type,
        specified by :param _type:, if possible.
        :param stream: #TODO what is stream for?

        WARNING: Not done.
        """
        # WARNING Not done.
        value = stream
        if _type == 0x0000:  # PtypUnspecified
            pass
        elif _type == 0x0001:  # PtypNull
            if value != b'\x00\x00\x00\x00\x00\x00\x00\x00':
                # DEBUG
                logger.warning('Property type is PtypNull, but is not equal to 0.')
            value = None
        elif _type == 0x0002:  # PtypInteger16
            value = constants.STI16.unpack(value)[0]
        elif _type == 0x0003:  # PtypInteger32
            value = constants.STI32.unpack(value)[0]
        elif _type == 0x0004:  # PtypFloating32
            value = constants.STF32.unpack(value)[0]
        elif _type == 0x0005:  # PtypFloating64
            value = constants.STF64.unpack(value)[0]
        elif _type == 0x0006:  # PtypCurrency
            value = (constants.STI64.unpack(value))[0] / 10000.0
        elif _type == 0x0007:  # PtypFloatingTime
            value = constants.STF64.unpack(value)[0]
            return constants.PYTPFLOATINGTIME_START + datetime.timedelta(days = value)
        elif _type == 0x000A:  # PtypErrorCode
            value = constants.STI32.unpack(value)[0]
            try:
                value = ErrorCodeType(value)
            except ValueError:
                logger.warn(f'Error type found that was not from Additional Error Codes. Value was {value}. You should report this to the developers.')
                # So here, the value should be from Additional Error Codes, but it
                # wasn't. So we are just returning the int. However, we want to see
                # if it is a normal error type.
                try:
                    logger.warn(f'REPORT TO DEVELOPERS: Error type of {ErrorType(value)} was found.')
                except ValueError:
                    pass
        elif _type == 0x000B:  # PtypBoolean
            value = constants.ST3.unpack(value)[0] == 1
        elif _type == 0x0014:  # PtypInteger64
            value = constants.STI64.unpack(value)[0]
        elif _type == 0x0040:  # PtypTime
            try:
                rawtime = constants.ST3.unpack(value)[0]
                if rawtime < 116444736000000000:
                    # We can't properly parse this with our current setup, so
                    # we will rely on olefile to handle this one.
                    value = olefile.olefile.filetime2datetime(rawtime)
                else:
                    if rawtime != 915151392000000000:
                        value = fromTimeStamp(filetimeToUtc(rawtime))
                    else:
                        # Temporarily just set to max time to signify a null date.
                        value = datetime.datetime.max
            except Exception as e:
                logger.exception(e)
                logger.error(f'Timestamp value of {filetimeToUtc(constants.ST3.unpack(value)[0])} caused an exception. This was probably caused by the time stamp being too far in the future.')
                logger.error(self.raw)
        elif _type == 0x0048:  # PtypGuid
            # TODO parsing for this
            pass
        return value

    @property
    def value(self):
        """
        Property value.
        """
        return self.__value


class VariableLengthProp(PropBase):
    """
    Class to contain the data for a single variable length property.
    """

    def __init__(self, string):
        super().__init__(string)
        self.__length, self.__reserved = constants.STVAR.unpack(string)
        if self.type == 0x001E:
            self.__realLength = self.__length - 1
        elif self.type == 0x001F:
            self.__realLength = self.__length - 2
        elif self.type in constants.MULTIPLE_2_BYTES_HEX:
            self.__realLength = self.__length // 2
        elif self.type in constants.MULTIPLE_4_BYTES_HEX:
            self.__realLength = self.__length // 4
        elif self.type in constants.MULTIPLE_8_BYTES_HEX:
            self.__realLength = self.__length // 8
        elif self.type in constants.MULTIPLE_16_BYTES_HEX:
            self.__realLength = self.__length // 16
        elif self.type == 0x000D:
            self.__realLength = None
        else:
            self.__realLength = self.__length

    @property
    def length(self):
        """
        The length field of the variable length property.
        """
        return self.__length

    @property
    def realLength(self):
        """
        The ACTUAL length of the stream that this property corresponds to.
        """
        return self.__realLength

    @property
    def reservedFlags(self):
        """
        The reserved flags field of the variable length property.
        """
        return self.__reserved
