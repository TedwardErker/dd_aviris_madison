# -*- coding: utf-8 -*-
"""
Created on Fri Mar 11 2016
Last version Thu Nov 17 2016
@author: Andy Ciurro
@author email: ahciurro@gmail.com

PURPOSE: Convert a multiband ENVI .hdr labeled image (.bil, .bsq, .bip) to a multiband GeoTIFF based on the specified parameters.

USE: To see parameters and usage, run from commandline with the -h switch enabled.

REQUIRED: You must also have Steve Kochaver's envi_header_handler.py in the same directory of this script to properly run.

"""

import sys, os, argparse, numpy
import envi_header_handler as EHH #Custom program written by Steve Cochaver

try:
    import gdal
except:
    try:
        from osgeo import gdal
    except:
        print "Import of gdal failed."
        sys.exit(1)

from gdalconst import *

def sortfilenames(src,dst):
    """
    Get absolute paths and directories from the input and output datasets.
    We really only need "inenvi" and "outgtif", but it can be nice to have other info printed to console.
    :param srcname: Source filename. Specified by -i flag.
    :param dstname: Destination filename. Specified by -o flag.
    """
    global inenvi
    inenvi = os.path.abspath(src)    
    inenvidir = os.path.dirname(src)
    inenvibn = os.path.basename(inenvi)
    global inenvihdr
    inenvihdr = inenvi + '.hdr'
    
    global outgtif
    outgtif = os.path.abspath(dst)
    wd = os.path.dirname(dst)
    outgtifbn = os.path.basename(outgtif)
    
    #Display names to console, if needed
    print 'inenvi:', inenvi
    if inenvidir is '':
        print 'inenvi directory: .'
    else:
        print 'inenvi directory:', inenvidir
    print 'inenvi basename:', inenvibn
    print 'output gtif:', outgtif
    if wd is '':
        print 'output directory: .'
    else:
        print 'output directory:', wd
    print 'output basename:', outgtifbn    
    
    #return inenvi, inenvihdr, outgtif
    
def parsebands(bandlist):
    """
    Parse through the bandlist, creating acceptable format. Might not be needed in most situations.
    :param bandlist: List of bands to copy to new geotiff. Specified by -b flag.
    """
    #Need code for "if bandlist == 'all'"
    global bands
    bands = bandlist
    print 'bands: ', bands
    
    #return bands
    
def parsescale(scalevals):
    global scale
    scale = scalevals
    print 'scale: ', scale
    
    #return scale
    
def parsedatatype(datatype):
    global dtype
    dtype = datatype
    if datatype is None:
        print 'output datatype: Float32'
    else:
        print 'output datatype:', dtype
        
    #return dtype

def parsenodata(nodataval):
    '''Needs fixing'''
    
    global nodata
    nodata = nodataval
    print 'NoData value:', nodata
    
    #return nodata

def get_info(src):
    """Gets some basic traits about the input image and its transformation matrix"""
                            
    #Register drivers and open image    
    gdal.AllRegister
    srcds = gdal.Open(inenvi, GA_ReadOnly)
    driver = srcds.GetDriver()
    driver.Register()
    if srcds is None:
        print 'Could not open', inenvi
        sys.exit(1)

    #Grab information about input image's driver, dimensions, and projection
    drivershort = driver.ShortName
    driverlong = driver.LongName
    global cols
    cols = srcds.RasterXSize
    global rows
    rows = srcds.RasterYSize
    proj = srcds.GetProjection()
    bandcount = srcds.RasterCount
    global rot_angle
    hdrinfo=EHH.ENVI_Header(inenvihdr)
    #rot_angle = EHH.extract_rotation(inenvihdr) # old version
    rot_angle = hdrinfo.get_rotation()
    print rot_angle
    #Display information to console, if needed
    print 'Driver:', drivershort, '/', driverlong
    print 'Size (x,y):', cols, ',', rows
    print 'Number of bands:', bandcount
    print 'Projection:', proj
    
    #This is where all of the transformation matrix information is gathered
    global geotransform
    global newGT
    #newGT=None
    #print newGT
    geotransform = srcds.GetGeoTransform()
    if not geotransform is None:
        topleftx = geotransform[0]
        toplefty = geotransform[3]
        pixelsizex = geotransform[1]
        pixelsizey = -1 * geotransform[5]
        rotfactorx = geotransform[2]
        rotfactory = geotransform[4]
        
        #Display information to console, if needed
        print 'Origin = (',topleftx,',',toplefty,')'
        print 'Pixel Size = (',pixelsizex,',',pixelsizey,')'
        print 'Rotation Factor = (',rotfactorx,',',rotfactory,')'
        
    #Close dataset
    srcds = None        
    
    #return cols, rows, rot_angle, geotransform
    
def rotationtransformation():

    import math
    indriver = gdal.GetDriverByName('ENVI')
    indriver.Register()
    srcds = gdal.Open(inenvi, GA_ReadOnly)
    if srcds is None:
        print 'Count not open', inenvi
        sys.exit(1)
        
    print '** Performing rotational tranformation with rotation angle of:', rot_angle, '**'
    
    if rot_angle == 0:
        xpixres = geotransform[1]
        xrotfactor = 0
        yrotfactor = xrotfactor
        ypixres = -1 * geotransform[5]
    else:
        #xpixres = geotransform[1] * math.cos(rot_angle*(math.pi/180))
        #xrotfactor = (-1) * geotransform[5] * math.sin(rot_angle*(math.pi/180))
        #yrotfactor = xrotfactor
        #ypixres = geotransform[5] * math.cos(rot_angle*(math.pi/180))
        xpixres = geotransform[1] * math.cos(-rot_angle*(math.pi/180))
        xrotfactor = (-1) * geotransform[1] * math.sin(-rot_angle*(math.pi/180))
        yrotfactor = geotransform[5] * math.sin(-rot_angle*(math.pi/180))
        ypixres = geotransform[5] * math.cos(-rot_angle*(math.pi/180))
        
    #global newGT        
    newGT = ((geotransform[0], xpixres, xrotfactor, geotransform[3], yrotfactor, ypixres))
    print newGT
    print "Rotation angle:", rot_angle
    print "x pixel resolution:", xpixres
    print "x rotation factor:", xrotfactor
    print "y rotation factor:", yrotfactor
    print "y pixel resolution:", ypixres
    print "upper left x:", geotransform[0]
    print "upper left y:", geotransform[3]
    return newGT
    
    
def create_copy(inenvi, outgtif,newGT):
    #print newGT
    #Read input image
    indriver = gdal.GetDriverByName('ENVI')
    indriver.Register()
    srcds = gdal.Open(inenvi, GA_ReadOnly)
    if srcds is None:
        print 'Count not open', inenvi
        sys.exit(1)
    
    #Create output image object
    outdriver = gdal.GetDriverByName('GTiff')
    outdriver.Register()
    #print dtype
    gdaltype_list={"Byte":gdal.GDT_Byte, \
                   "CFloat32":GDT_CFloat32,\
                   "CFloat64":GDT_CFloat64, \
                   "CInt16":GDT_CInt16,\
                   "CInt32":GDT_CInt32,\
                   "Float32":GDT_Float32,\
                   "Float64":GDT_Float64,\
                   "Int16":GDT_Int16,\
                   "Int32":GDT_Int32,\
                   "UInt16":GDT_UInt16,\
                   "UInt32":GDT_UInt32,\
                  }
    #print gdaltype_list[dtype]
    #sys.exit(0)
    if dtype is not None:
        dst_ds = outdriver.Create(outgtif, cols, rows, len(bands), gdaltype_list[dtype])
        
    else:
        dst_ds = outdriver.Create(outgtif, cols, rows, len(bands), gdal.GDT_Float32)

    if dst_ds is None:
        print 'Could not create', outgtif
        sys.exit(1)
    
    #Sets spatial reference to the same as input image
    srcPrjWkt = srcds.GetProjection()
    dst_ds.SetProjection(srcPrjWkt)   
    #print newGT 
    #sys.exit(1)
    if newGT is not None:
        dst_ds.SetGeoTransform(newGT)
    else:
        dst_ds.SetGeoTransform(geotransform)
    
    #Get the bands and calculate their natural block size
    outbandcount = 1
    for bandnumber in bands:
        inband = srcds.GetRasterBand(bandnumber)
        if inband is None:
            print 'Could not get inband number', bandnumber
            exit(1)
        blkSizeX = inband.GetBlockSize()[0]
        blkSizeY = inband.GetBlockSize()[1]
        #print 'source NoData value of band', bandnumber, ':', inband.GetNoDataValue()
        outband = dst_ds.GetRasterBand(outbandcount) #Output image writes band numbers starting at 1 
        if outband is None:                          #This is why we use our counter rather than the variable "bandnumber"
            print 'Could not get outband'
            exit(1)
        
        #For images that are read by scanline (i.e. one row at a time/most ENVI images)
        if blkSizeY == 1:
            for i in range(rows):
                #print i
                data = inband.ReadAsArray(0, i, cols, 1).astype(numpy.float)
                
                #scales data if -s was indicated
                #explanation: http://stackoverflow.com/questions/5294955/how-to-scale-down-a-range-of-numbers-with-a-known-min-and-max-value
                if scale is not None:
                    origmin = scale[0]
                    origmax = scale[1]
                    newmin = scale[2]
                    newmax = scale[3]
                    data = (((newmax-newmin)*(data-origmin))/(origmax-origmin)) + newmin
                    
                outband.WriteArray(data, xoff=0, yoff=i)
        
        #For images that are tiled
        else:
            for i in range(0, rows, blkSizeY):
                if i + blkSizeY < rows:
                    numRows = blkSizeY
                else:
                    numRows = rows - i
                for j in range(0, cols, blkSizeX):
                    if j + blkSizeX < cols:
                        numCols = blkSizeX
                    else:
                        numCols = cols - j
                    data = inband.ReadAsArray(j, i, numCols, numRows).astype(numpy.float)
                    
                    #scales data if -s was indicated
                    #explanation: http://stackoverflow.com/questions/5294955/how-to-scale-down-a-range-of-numbers-with-a-known-min-and-max-value
                    if scale is not None:
                        origmin = scale[0]
                        origmax = scale[1]
                        newmin = scale[2]
                        newmax = scale[3]
                        data = (((newmax-newmin)*(data-origmin))/(origmax-origmin)) + newmin 
                    
                    if data is None:
                        print 'Could not read input data'
                        exit(1) 
                    dst_ds.GetRasterBand(outbandcount).WriteArray(data, xoff=j, yoff=1)
                    
        if nodata is not None:                    
            outband.SetNoDataValue(nodata)
            #print 'outband nodata value:', outband.GetNoDataValue()
        outbandcount += 1
    
    #Close datasets
    srcds = None
    dst_ds = None
            
def argument_parser(args):
    """
    Parse throught the command-line arguments and assign the values to a variable.
    Stores them in a dictionary named args
    """
    print('args: {}'.format(args))
    desc = 'envi2gtif will read an ENVI image and its associated header file (.hdr) and then create a GeoTIFF based on the specified parameters. \
            Requires Steve Kochaver\'s envi_header_handler.py'
    parser = argparse.ArgumentParser(description = desc)
    parser.add_argument('-b', action = 'store', dest = 'bandlist', nargs = '+', type = int, required = True,
                        help = '<b1 b2 b3 ...>; list of input bands, separated by spaces')
    parser.add_argument('-i', action = 'store', dest = 'srcname', type = str, required = True,
                        help = '<inenvi>; source envi file, without extension')
    parser.add_argument('-o', action = 'store', dest = 'dstname', type = str, required = True,
                        help = '<outgtif>; destination geotiff')
    parser.add_argument('-s', action = 'store', dest = 'scale', nargs = 4, type = int, required = False,
                        help = '<srcmin srcmax dstmin dstmax>; min & max scale values, separated by spaces')
    parser.add_argument('-n', action = 'store', dest = 'nodataval', type = float,
                        help = '<nodataval>; assign a single nodata value to output')
    parser.add_argument('-t', action = 'store', dest = 'datatype', type = str,
                        help = 'Byte/CFloat32/CFloat64/CInt16/CInt32/Float32/Float64/Int16/Int32/UInt16/UInt32; \
                        these are the supported datatypes for GDAL. Defaults as Float32.')    
    parser.add_argument('-r', action = 'store_true', dest = 'dorotation',
                        help = 'no argument; apply \"un\"-rotation based on envi .hdr')    
    args_dict = parser.parse_args(args).__dict__ 
    return args_dict    
    
def main():
    args = argument_parser(sys.argv[1:])
    sortfilenames(args['srcname'], args['dstname'])
    print '-----------------------------------------'
    parsebands(args['bandlist'])
    parsescale(args['scale'])
    parsenodata(args['nodataval'])
    parsedatatype(args['datatype'])
    print '.........................................'
    get_info(inenvi)

    newGT=None

    if args['dorotation'] == True:
        newGT=rotationtransformation()
    print '*****************************************'
    #sys.exit(0)
    create_copy(inenvi, outgtif, newGT)
    
if __name__ == "__main__":
    main()