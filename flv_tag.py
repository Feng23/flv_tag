#!/usr/bin/env python

import sys
from flv_tag_object import *

def read_flv(fname):
    with open(fname) as f:
        tmp = f.read(FLV_HEADER_LENGTH)
        if tmp[:3] != 'FLV':
            print >>sys.stderr, 'file',fname,'is not flv file'
            exit(1)
        while tmp:
            print_title("PriviousTagSize")
            print FlvPriviousTagSize(f)
            print_tag('Position', f.tell())

            try:
                flvTag = FlvTag(f)
            except:
                print_title('Over')
                break
            print_title("FlvTag")
            print flvTag

            if flvTag.TagType.value is 8: #AudioTagHeader
                audioTagHeader = FlvAudioTagHeader(f)
                print_title("AudioTagHeader")
                print audioTagHeader
                f.read(flvTag.DataSize.value - audioTagHeader.length)
            elif flvTag.TagType.value is 9:   #VideoTagHeader
                videoTagHeader = FlvVidioTagHeader(f)
                print_title("VideoTagHeader")
                print videoTagHeader
                f.read(flvTag.DataSize.value - videoTagHeader.length)
            else:   #skip scriptdata
                f.read(flvTag.DataSize.value)

            if flvTag.Filter.value is 1:  #EncryptionHeader, FilterParams 
                pass

def main():
    if len(sys.argv) is not 2:
        print >>sys.stderr, "Usage: %s flv_file_name" %sys.argv[0]
        exit(1)
    read_flv(sys.argv[1])

if __name__ == '__main__':
    main()
