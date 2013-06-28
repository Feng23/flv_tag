#!/usr/bin/env python

import struct

FLV_HEADER_LENGTH = 9
FLV_TAG_HEADER_LENGTH = 11
TITLE_WIDTH = 80
TITLE_FILLCHAR = '-'
TAG_LEFT_LENGTH = 20

def print_title(s):
    print s.rjust((TITLE_WIDTH + len(s))/2, TITLE_FILLCHAR).ljust(TITLE_WIDTH, TITLE_FILLCHAR)

def print_tag(name, value):
    print "%s%s" %(name.ljust(TAG_LEFT_LENGTH), value)

class UnkownUINTError(Exception):
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return "%d" %self.value

class UnkownUBYTEError(UnkownUINTError):
    def __init__(self, offset, bitnum):
        self.offset = offset
        self.bitnum = bitnum
    def __repr__(self):
        return "%d, %d" %(self.offset, self.bitnum)

class UINT:
    def __init__(self, bytenum, comment = {}):
        if bytenum not in [1, 2, 3, 4]:
            raise UnkownUINTError(bytenum)
        self.bytenum = bytenum
        self.comment = comment
    def parse(self, s):
        if self.bytenum is 1:
            self.value = struct.unpack('B', s)[0]
        elif self.bytenum is 2:
            self.value = struct.unpack('>H', s)[0]
        elif self.bytenum is 3:
            self.value = struct.unpack('>I', '\x00' + s)[0]
        elif self.bytenum is 4:
            self.value = struct.unpack('>I', s)[0]
    def __str__(self):
        if self.comment.get(self.value):
            return "%s" %self.comment[self.value]
        else:
            return self.rawstr()
    def rawstr(self):
        return "%d" %self.value

class UBYTE:
    def __init__(self, offset, bitnum, comment = {}):
        if offset not in range(0, 8) or bitnum + offset not in range(1, 9):
            raise UnkownUBYTEError(offset, bitnum)
        self.offset = 8 - offset - bitnum   #offset
        self.bitnum = bitnum
        self.mask = 1
        for i in range(bitnum - 1):
            self.mask = (self.mask<<1) + 1
        self.comment = comment
    def parse(self, d):
        self.value = d>>self.offset&self.mask
    def __str__(self):
        if self.comment.get(self.value):
            return "%s" %self.comment[self.value]
        else:
            return self.rawstr()
    def rawstr(self):
        return "%d" %self.value

class UnknownType:
    pass

class Tag:
    def __init__(self, f):
        self.f = f
        self.instantiate()
    def instantiate(self):
        byte_offset = 0
        for tag in self.taglist:
            tmptag = getattr(self, tag)
            if tmptag.__class__ is UINT:
                self.instantiate_uint(tmptag)
            elif tmptag.__class__ is UBYTE:
                if byte_offset is 0:
                    ui8 = UINT(1)
                    ui8.parse(self.f.read(1))
                tmptag.parse(ui8.value)
                byte_offset = tmptag.offset + tmptag.bitnum
                if byte_offset is 7:
                    byte_offset = 0
            elif tmptag.__class__ is UnknownType:
                self.determine_type()   #Determine type dynamically
    def instantiate_uint(self, tag):
        tag.parse(self.f.read(tag.bytenum))
    def __str__(self):
        tmp = []
        for tag in self.taglist:
            tmp.append("%s%s" %(tag.ljust(TAG_LEFT_LENGTH), getattr(self, tag))) 
        return '\n'.join(tmp)

class FlvTag(Tag):
    Reserved = UBYTE(0, 2)
    Filter = UBYTE(2, 1, {
        0: '0 = No pre-processing required',
        1: '1 = Pre-processing'
        })
    TagType = UBYTE(3, 5, {
        8: "8 = audio",
        9: "9 = video",
        18: "18 = script data"
        })
    DataSize = UINT(3)
    Timestamp = UINT(3)
    TimestampExtended = UINT(1)
    StreamID = UINT(3)
    def __init__(self, f):
        self.taglist = (
                "Reserved",
                "Filter",
                "TagType",
                "DataSize",
                "Timestamp",
                "TimestampExtended",
                "StreamID"
                )
        Tag.__init__(self, f)

class FlvPriviousTagSize(Tag):
    PriviousTagSize = UINT(4)
    def __init__(self, f):
        self.taglist = ("PriviousTagSize",)
        Tag.__init__(self, f)

class FlvAudioTagHeader(Tag):
    SoundFormat = UBYTE(0, 4, {
        0: "Linear PCM, platform endian",
        1: "ADPCM",
        2: "MP3",
        3: "Linear PCM, little endian",
        4: "Nellymoser 16 kHz mono",
        5: "Nellymoser 8 kHz mono",
        6: "Nellymoser",
        7: "G.711 A-law logarithmic PCM",
        8: "G.711 mu-law logarithmic PCM",
        9: "reserved",
        10: "AAC",
        11: "Speex",    #11
        14: "MP3 8 kHz",    #14
        15: "Device-specific sound"
        })
    SoundRate = UBYTE(4, 2, {
        0: "5.5kHz",
        1: "11kHz",
        2: "22kHz",
        3: "44kHz",
        })
    SoundSize = UBYTE(6, 1, {
        0: "8-bit samples",
        1: "16-bit samples"
        })
    SoundType = UBYTE(7, 1, {
        0: "Mono sound",
        1: "Stereo sound" 
        })
    AACPacketType = UnknownType()
    def __init__(self, f):
        self.taglist = (
                "SoundFormat",
                "SoundRate",
                "SoundSize",
                "SoundType"
                )
        self.length = 1
        Tag.__init__(self, f)
    def determine_type(self):
        if self.SoundFormat.value is 10:
            self.AACPacketType = UINT(1, {
                0: "AAC sequence header",
                1: "AAC raw"
                })
            self.instantiate_uint(self.AACPacketType)
            self.length += 1

class FlvVidioTagHeader(Tag):
    FrameType = UBYTE(0, 4, {
        1: "key frame (for AVC, a seekable frame)",
        2: "inter frame (for AVC, a non-seekable frame)",
        3: "disposable inter frame (H.263 only)",
        4: "generated key frame (reserved for server use only)",
        5: "video info/command frame"
        })
    CodecID = UBYTE(4, 4, {
        2: "Sorenson H.263",
        3: "Screen video",
        4: "On2 VP6",
        5: "On2 VP6 with alpha channel",
        6: "Screen video version 2",
        7: "AVC"
        })
    def __init__(self, f):
        self.taglist = (
                "FrameType",
                "CodecID"
                )
        self.length = 1
        Tag.__init__(self, f)

class FlvSCRIPTDATAVALUE (Tag):
    Type = UINT(1, {
        0: "0 = Number",
        1: "1 = Boolean",
        2: "2 = String",
        3: "3 = Object",
        4: "4 = MovieClip (reserved, not supported)",
        5: "5 = Null",
        6: "6 = Undefined",
        7: "7 = Reference",
        8: "8 = ECMA array",
        9: "9 = Object end marker",
        10: "10 = Strict array",
        11: "11 = Date",
        12: "12 = Long string"
        })
    ScriptDataValue = UnknownType()
    def __init__(self, f):
        self.taglist = ("Type", "ScriptDataValue")
        Tag.__init__(self, f)
    def determine_type(self):
        if self.Type.value is 0:
            pass
        elif self.Type.value is 1:
            self.ScriptDataValue = UINT(1)
            self.instantiate_uint(self.ScriptDataValue)
        elif self.Type.value is 2:
            self.ScriptDataValue = FlvSCRIPTDATASTRING(self.f)
    def __str__(self):
        return str(self.ScriptDataValue)

class FlvSCRIPTDATASTRING(Tag):
    StringLength = UINT(2)
    StringData = UnknownType()
    def __init__(self, f):
        self.taglist = ("StringLength", "StringData")
        Tag.__init__(self, f)
    def determine_type(self):
        self.StringData = self.f.read(self.StringLength.value)
    def __str__(self):
        return self.StringData
        #return str(self.StringLength)

class FlvSCRIPTDATAECMAARRAY(Tag):
    ECMAArrayLength = UINT(4)
    Variables = None
    ListTerminator = None
    def __init__(self, f):
        self.taglist = ("ECMAArrayLength", "Variables", "ListTerminator")
        Tag.__init__(self, f)
