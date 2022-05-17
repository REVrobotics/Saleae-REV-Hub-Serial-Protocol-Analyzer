from typing import Optional

from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame, NumberSetting

GENERIC_CMD_FRAME_TYPE = 'rhsp_generic_cmd'
KNOWN_CMD_FRAME_TYPE = 'rhsp_known_cmd'
GENERIC_RESP_FRAME_TYPE = 'rhsp_generic_resp'
KNOWN_RESP_FRAME_TYPE = 'rhsp_known_resp'
I2C_CMD_FRAME_TYPE = 'rhsp_i2c_cmd'

class Hla(HighLevelAnalyzer):
    DEKAInterfaceFirstId = NumberSetting()

    result_types = {
        GENERIC_CMD_FRAME_TYPE: {
            'format': 'RHSP cmd={{data.cmd}} msg={{data.msgNum}}'
        },
        KNOWN_CMD_FRAME_TYPE: {
            'format': 'RHSP {{data.packetTypeName}} msg={{data.msgNum}}'
        },
        GENERIC_RESP_FRAME_TYPE: {
            'format': 'RHSP response ref={{data.refNum}} (msg={{data.msgNum}})'
        },
        KNOWN_RESP_FRAME_TYPE: {
            'format': 'RHSP {{data.packetTypeName}} ref={{data.refNum}} (msg={{data.msgNum}})'
        },
        I2C_CMD_FRAME_TYPE: {
            'format': 'RHSP {{data.packetTypeName}} bus={{data.i2cBus}} addr={{data.i2cAddr}} reg={{data.i2cReg}} length={{data.i2cLength}} msg={{data.msgNum}}'
        }
    }

    def __init__(self):
        self.currentPacket: Optional[bytearray] = None
        self.currentPacketStartTime = None
        self.packetLengthBytes: Optional[bytearray] = None
        self.packetLength = 0

    def clearCurrentPacket(self):
        self.currentPacket = None
        self.currentPacketStartTime = None
        self.packetLengthBytes = None
        self.packetLength = 0

    def decode(self, frame: AnalyzerFrame):
        byte: int = frame.data['data'][0]

        if self.currentPacket is None:
            if byte == 0x44:
                self.currentPacket = bytearray([byte])
                self.currentPacketStartTime = frame.start_time
            else:
                self.clearCurrentPacket()
        else:
            self.currentPacket.append(byte)
            bytesReceived = len(self.currentPacket)

            if bytesReceived == 2 and byte != 0x4B:
                self.clearCurrentPacket()
            elif bytesReceived == 3:
                # Read the first length byte
                self.packetLengthBytes = bytearray([byte])
            elif bytesReceived == 4:
                # Read the second length byte
                self.packetLengthBytes.append(byte)
                self.packetLength = int.from_bytes(self.packetLengthBytes, 'little')
            elif bytesReceived == self.packetLength:
                msgNum = self.currentPacket[6]
                refNum = self.currentPacket[7]
                typeId = int.from_bytes(self.currentPacket[8:10], 'little')
                payload: bytearray = self.currentPacket[10:-1]
                frameType = GENERIC_RESP_FRAME_TYPE
                packetTypeName = 'Response'

                i2cBus = ""
                i2cAddr = ""
                i2cReg = ""
                i2cLength = ""

                if typeId == 0x7F01:
                    frameType = KNOWN_RESP_FRAME_TYPE
                    packetTypeName = 'ACK'
                elif typeId == 0x7F02:
                    frameType = KNOWN_RESP_FRAME_TYPE
                    packetTypeName = 'NACK'
                elif typeId == 0x7F03:
                    frameType = KNOWN_CMD_FRAME_TYPE
                    packetTypeName = 'GetModuleStatus'
                elif typeId == 0x7F04:
                    frameType = KNOWN_CMD_FRAME_TYPE
                    packetTypeName = 'KeepAlive'
                elif typeId == 0x7F05:
                    frameType = KNOWN_CMD_FRAME_TYPE
                    packetTypeName = 'FailSafe'
                elif typeId == 0x7F06:
                    frameType = KNOWN_CMD_FRAME_TYPE
                    packetTypeName = 'SetNewModuleAddress'
                elif typeId == 0x7F07:
                    frameType = KNOWN_CMD_FRAME_TYPE
                    packetTypeName = 'QueryInterface'
                elif typeId == 0x7F0C:
                    frameType = KNOWN_CMD_FRAME_TYPE
                    packetTypeName = 'SetModuleLEDPattern'
                elif typeId == 0x7F0D:
                    frameType = KNOWN_CMD_FRAME_TYPE
                    packetTypeName = 'GetModuleLEDPattern'
                elif typeId == 0x7F0E:
                    frameType = KNOWN_CMD_FRAME_TYPE
                    packetTypeName = 'DebugLogLevel'
                elif typeId == 0x7F0F:
                    frameType = KNOWN_CMD_FRAME_TYPE
                    packetTypeName = 'Discovery'
                elif typeId == self.DEKAInterfaceFirstId + 37:
                    frameType = I2C_CMD_FRAME_TYPE
                    packetTypeName = 'I2cWriteSingleByte'
                    i2cBus = payload[0]
                    i2cAddr = hex(payload[1])
                    i2cLength = 0
                elif typeId == self.DEKAInterfaceFirstId + 38:
                    frameType = I2C_CMD_FRAME_TYPE
                    packetTypeName = 'I2cWriteMultipleBytes'
                    i2cBus = payload[0]
                    i2cAddr = hex(payload[1])
                    i2cReg = hex(payload[3])
                    # Subtract the register byte
                    i2cLength = payload[2] - 1
                elif typeId == self.DEKAInterfaceFirstId + 39:
                    frameType = I2C_CMD_FRAME_TYPE
                    packetTypeName = 'I2cReadSingleByte'
                    i2cBus = payload[0]
                    i2cAddr = hex(payload[1])
                    i2cLength = 1
                elif typeId == self.DEKAInterfaceFirstId + 40:
                    frameType = I2C_CMD_FRAME_TYPE
                    packetTypeName = 'I2cReadMultipleBytes'
                    i2cBus = payload[0]
                    i2cAddr = hex(payload[1])
                    i2cLength = payload[2]
                elif typeId == self.DEKAInterfaceFirstId + 41:
                    frameType = KNOWN_CMD_FRAME_TYPE
                    packetTypeName = 'I2cReadStatusQuery'
                elif typeId == self.DEKAInterfaceFirstId + 42:
                    frameType = KNOWN_CMD_FRAME_TYPE
                    packetTypeName = 'I2cWriteStatusQuery'
                elif typeId == self.DEKAInterfaceFirstId + 52:
                    frameType = I2C_CMD_FRAME_TYPE
                    packetTypeName = 'I2cWriteReadMultipleBytes'
                    i2cBus = payload[0]
                    i2cAddr = hex(payload[1])
                    i2cReg = hex(payload[3])
                    i2cLength = payload[2]
                elif refNum == 0:
                    frameType = GENERIC_CMD_FRAME_TYPE
                    packetTypeName = 'Command'

                result = AnalyzerFrame(frameType, self.currentPacketStartTime, frame.end_time, {
                    'cmd': hex(typeId),
                    'packetTypeName': packetTypeName,
                    'msgNum': msgNum,
                    'refNum': refNum,
                    'i2cBus': i2cBus,
                    'i2cAddr': i2cAddr,
                    'i2cReg': i2cReg,
                    'i2cLength': i2cLength,
                })
                self.clearCurrentPacket()
                return result
