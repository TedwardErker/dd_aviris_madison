#!/usr/bin/python

# based on aviris_tcld_sav2.pro
# Create mask

import numpy as np
#from scipy import stats # for linear regression
#import scipy.ndimage.filters as filter
from scipy.stats import norm
import scipy.signal as sig
import gdal#, osr
from gdalconst import *
from osgeo import osr
import sys, argparse, os.path
import re#string, re
#import math
import struct # for band reading
import envi_header_handler


#/usr/bin/anaconda2/bin/python h:/test/aviris_ng_tcld_py5.py -i h:/test/aviris/ang20150901t180713_corr_v1h_img -o h:/test/aviris/ > h:/test/aviris/csm_test_ang20150901t180713.txt

# v3: add envi_header_handler, do not use ReadAsArray()

def remove_hdr_item(hdr, itemkey):
  if itemkey in hdr._key_order: hdr._key_order.remove(itemkey)
  if itemkey in hdr._nested_keys: hdr._nested_keys.remove(itemkey)
  hdr.hdr_dict.pop(itemkey, None)	

def add_hdr_item(hdr, itemkey, value, nested):
  if itemkey in hdr._key_order: return
  if itemkey in hdr._nested_keys: return
  
  if nested ==2: hdr._nested_keys.append(itemkey)
  hdr._key_order.append(itemkey)
  hdr.hdr_dict[itemkey]=value

def gdaltype2nptype(gdalDataType):
  typelist=['B','H','h','I','i','f']
  fmt=typelist[gdalDataType-1]
  return fmt


def read_array(in_band):
# use gdal function
  typelist=['B','H','h','I','i','f']
  scanline = in_band.ReadRaster( 0, 0, in_band.XSize, in_band.YSize, in_band.XSize, in_band.YSize, in_band.DataType )
  fmt=typelist[in_band.DataType-1]
  #print fmt
  #print scanline
  value = struct.unpack(fmt * in_band.XSize*in_band.YSize, scanline)
  # http://geoinformaticstutorial.blogspot.com/2012/09/reading-raster-data-with-python-and-gdal.html

  #sys.exit(1) 
  value=np.array(value)
  #print value.shape
  return np.reshape(value,(in_band.YSize,in_band.XSize))

def read_bip2array(inimg,b_ind,nband,ysize,xsize,gdaldtype):
  binf=open(inimg,"rb")
  sub_nband=len(b_ind)
  #print sub_nband
  outdata=np.zeros((ysize,xsize,sub_nband),np.dtype(gdaltype2nptype(gdaldtype)))
  #print outdata.shape
  for iline in range(ysize):
    line_data=np.fromfile(binf,dtype=np.dtype(gdaltype2nptype(gdaldtype)), count = xsize*nband)
    #print line_data.shape
    line_data=np.reshape(line_data,(nband,xsize),order='F')
    #print line_data[:,[x-1 for x in b_ind]].shape, outdata.shape
    for ii in range(sub_nband):
      outdata[iline,:,ii]=line_data[b_ind[ii]-1,:]
    #line_data=np.reshape(line_data[:,[x-1 for x in b_ind]],(1,xsize,sub_nband))
    #:print line_data.shape,outdata[iline,:,:].shape
    #outdata[iline,:,:]=line_data
   
  binf=None
  return outdata

def read_bil2array(inimg,b_ind,nband,ysize,xsize,gdaldtype):
  binf=open(inimg,"rb")
  sub_nband=len(b_ind)
  #print sub_nband
  outdata=np.zeros((ysize,xsize,sub_nband),np.dtype(gdaltype2nptype(gdaldtype)))
  #print outdata.shape
  for iline in range(ysize):
    line_data=np.fromfile(binf,dtype=np.dtype(gdaltype2nptype(gdaldtype)), count = xsize*nband)
    #print line_data.shape
    line_data=np.reshape(line_data,(xsize,nband),order='F').T
    #print line_data[:,[x-1 for x in b_ind]].shape, outdata.shape
    for ii in range(sub_nband):
      outdata[iline,:,ii]=line_data[b_ind[ii]-1,:]
    #line_data=np.reshape(line_data[:,[x-1 for x in b_ind]],(1,xsize,sub_nband))
    #:print line_data.shape,outdata[iline,:,:].shape
    #outdata[iline,:,:]=line_data
   
  binf=None
  return outdata

def read_bsq2array(inimg,b_ind,nband,ysize,xsize,gdaldtype):
  binf=open(inimg,"rb")
  sub_nband=len(b_ind)
  d_size=np.dtype(gdaltype2nptype(gdaldtype)).itemsize
  #print sub_nband
  outdata=np.zeros((ysize,xsize,sub_nband),np.dtype(gdaltype2nptype(gdaldtype)))
  #print outdata.shape
  for ii in range(sub_nband):
    binf.seek(d_size*xsize*ysize*b_ind[ii],0)
    band_data=np.fromfile(binf,dtype=np.dtype(gdaltype2nptype(gdaldtype)), count = xsize*ysize)
    outdata[:,:,ii]=np.reshape(band_data,(ysize,xsize))
    
  binf=None
  return outdata  
 
  
def shd_mask(in_ds, bad_mask, bkgMask, kernel,inimg,totalnband,gdaltype, interleave):

  nband=5  # 25
  l_POS=np.array(range(nband))+167
  # 1.17~ 1.29
  b_ind=[x+167 for x in range(nband)]
  if interleave=='bip':
    bkgFill=read_bip2array(inimg,b_ind,totalnband,in_ds.RasterYSize, in_ds.RasterXSize,gdaltype)
  if interleave=='bil':
    bkgFill=read_bil2array(inimg,b_ind,totalnband,in_ds.RasterYSize, in_ds.RasterXSize,gdaltype)  
  if interleave=='bsq':
    bkgFill=read_bsq2array(inimg,b_ind,totalnband,in_ds.RasterYSize, in_ds.RasterXSize,gdaltype) 

  ##bkgFill=np.zeros((in_ds.RasterYSize, in_ds.RasterXSize,nband))
  ##return 1-bkgFill[:,:,0]###########################temp
  rBand=np.random.randn(in_ds.RasterYSize,in_ds.RasterXSize)
  thres=3
  rand_count=len(rBand[(rBand>thres) & (bad_mask>0)])
  print rand_count  

  y_ind=np.where((rBand>thres) & (bad_mask>0))[0]
  x_ind=np.where((rBand>thres) & (bad_mask>0))[1]

  indata=np.zeros((rand_count,nband),gdaltype2nptype(gdaltype))
  for ii in range(rand_count):
    indata[ii,:]=bkgFill[y_ind[ii],x_ind[ii],:]

  cov_mat=np.cov(indata.T)


  ##count=len(bad_mask[bad_mask < 0])
  ##for i in range(nband):
    #iBand=in_ds.GetRasterBand(l_POS[i]+1).ReadAsArray().astype(np.float32)
  ##  iBand=read_array(in_ds.GetRasterBand(l_POS[i]+1)).astype(np.float32)
  ##  if (count > 0):
  ##    rBand=np.random.randn(in_ds.RasterYSize, in_ds.RasterXSize)
  #3    iBand[bad_mask < 0]=rBand[bad_mask < 0]
    
  ##  bkgFill[:,:,i]=iBand

  bkgFill_re=np.reshape(bkgFill,(in_ds.RasterYSize*in_ds.RasterXSize,nband))  # change to n rows by 15 columns
  mean_vec=np.mean(bkgFill_re, axis=0)
  ##cov_mat=np.cov(bkgFill_re.T)  # change to 15 rows by n columns, cov matrix 15by15

  endmember=np.zeros(nband)
  
  # Matched Filtering
  del1=endmember-mean_vec
  del2=bkgFill_re-mean_vec
  denominator=np.sum(np.dot(del1,cov_mat)*del1)  # scalar
  numerator=np.sum(np.dot(del2,cov_mat)*del1,axis=1)
  #print del1.shape
  #print del2.shape
  #print np.dot(del2,cov_mat).shape, numerator.shape
  #sys.exit(0)
  mf_out=np.reshape(numerator/denominator,(in_ds.RasterYSize,in_ds.RasterXSize))
  #sys.exit(0)
  shdBand=mf_out*1000
  shdBand = sig.convolve(shdBand,kernel, mode = 'same')  #mean filter
  #shdBand=MEAN_FILTER(shdBand,3,3,/ARITHMETIC)
  
  shdTest=shdBand
  shd_Ind=(shdBand > 400) #400
  count=len(shdTest[shd_Ind])
  if (count > 0):
    shdBand[shd_Ind]=0
    shdBand[shdBand!= 0]=1
    shdBand[bkgMask == 0]=0

  return shdBand
  
#########################################################

def cld_mask(in_ds ,bad_mask,shdBand,inimg, totalnband, gdaltype, interleave):

  #iPos=range(149,153)#range(106,110)+range(149,153)  # 1.353~1.383  1.7816~1.8115
  #iPos=range(106,110)+range(149,153)
  #iPos=[152]#[152, 153]
  
  iPos=[290,326]#[106, 112, 152, 153, 167, 168, 169]#[106, 107, 108, 109, 110, 111, 112, 152, 153, 167, 168, 169]#1.353, 1.4129, 1.8115, 1.8214, 1.9373~1.9573
  nbb=len(iPos)#7
  print iPos, nbb
  iEnd=np.zeros(nbb)#(4)#(8)
  
  if interleave=='bip':
    wrtArr=read_bip2array(inimg,iPos,totalnband,in_ds.RasterYSize, in_ds.RasterXSize,gdaltype)
  if interleave=='bil':
    wrtArr=read_bil2array(inimg,iPos,totalnband,in_ds.RasterYSize, in_ds.RasterXSize,gdaltype)
  if interleave=='bsq':
    wrtArr=read_bsq2array(inimg,iPos,totalnband,in_ds.RasterYSize, in_ds.RasterXSize,gdaltype)
  ##wrtArr=np.zeros((in_ds.RasterYSize,in_ds.RasterXSize,nbb))#wrtArr=np.zeros((in_ds.RasterYSize,in_ds.RasterXSize,8))
  #tBmax=0

  kernelSize5 = [5, 5] 
  kernel5 = np.zeros((kernelSize5[0],kernelSize5[1]))+1./((kernelSize5[0]*kernelSize5[1])) 
  
  count=len(bad_mask[bad_mask < 0])
  #print count
  for i in range(nbb):#range(8)
    #iBand=in_ds.GetRasterBand(iPos[i]+1).ReadAsArray().astype(np.float32)
  ##  iBand=read_array(in_ds.GetRasterBand(iPos[i]+1)).astype(np.float32)
    iBand=wrtArr[:,:,i]
    iBave=np.median(iBand[iBand>=0])
    iBmax=5*iBave
    iEnd[i]=iBmax

    if (count>0):
      rBand=np.random.randn(in_ds.RasterYSize, in_ds.RasterXSize)+iBmax
      iBand[bad_mask < 0]=rBand[bad_mask < 0]      

 
    iBand = sig.convolve(iBand,kernel5, mode = 'same')  #mean filter
    wrtArr[:,:,i]=iBand
  print iEnd
  #sys.exit(0)
  
  rBand=np.random.randn(in_ds.RasterYSize,in_ds.RasterXSize)
  thres=3
  rand_count=len(rBand[(rBand>thres) & (bad_mask>0)])
  print rand_count

  y_ind=np.where((rBand>thres) & (bad_mask>0))[0]
  x_ind=np.where((rBand>thres) & (bad_mask>0))[1]

  indata=np.zeros((rand_count,nbb),gdaltype2nptype(gdaltype))
  for ii in range(rand_count):
    indata[ii,:]=wrtArr[y_ind[ii],x_ind[ii],:]

  cov_mat=np.cov(indata.T)


  wrtArr_re=np.reshape(wrtArr,(in_ds.RasterYSize*in_ds.RasterXSize,nbb))#wrtArr_re=np.reshape(wrtArr,(in_ds.RasterYSize*in_ds.RasterXSize,8))  # change to n rows by 8 columns
  mean_vec=np.mean(wrtArr_re, axis=0)
  #cov_mat=np.cov(wrtArr_re.T)  # change to 8 rows by n columns, cov matrix 8by8
	
  # Matched Filtering
  del1=iEnd-mean_vec
  del2=wrtArr_re-mean_vec
  denominator=np.sum(np.dot(del1,cov_mat)*del1)  # scalar
  numerator=np.sum(np.dot(del2,cov_mat)*del1,axis=1)
  mf_out=np.reshape(numerator/denominator,(in_ds.RasterYSize,in_ds.RasterXSize))  
  #return mf_out
  cldBand=mf_out*1000
  cldBand = sig.convolve(cldBand,kernel5, mode = 'same')  #mean filter
  
  # GET MEAN AND SD OF CLOUD PIXELS
  cldHist=cldBand[shdBand == 1]
  (iHist,iLocs)=np.histogram(cldHist,bins=256)
  iLocs=0.5*(iLocs[1:]+iLocs[:-1])
  #print iHist.shape, iLocs.shape  (256L,)  (257L,)  
  #print iHist
  #print iLocs
  #Remove data for the 0 loc
  iHist=iHist.astype(np.float32)
  iHist=iHist[iLocs != 0]#iHist=iHist[iLocs[:-1] != 0]
  iLocs=iLocs[iLocs != 0]
  #print iHist
  #print iLocs  
  hInds=range(len(iHist))
  # ...get max value after the zero
  gt0_Hist=iHist[iLocs < 0]#gt0_Hist=iHist[iLocs[:-1] < 0]
  gt0_Locs=iLocs[iLocs < 0]
  #print gt0_Hist
  #print gt0_Locs 
  gt0_MaxH=np.amax(gt0_Hist)
  gt0_MaxI=np.argmax(gt0_Hist)
  
  print gt0_MaxH,gt0_MaxI
  
  #SET UP CONDITION WHEN THE MAX OCCURS RIGHT AT THE START OF THE HISTOGRAM
  if (gt0_MaxI > 0):
    # ...get part of histogram beyond gt0_MaxL, reverse
    swapHist=iHist[:(gt0_MaxI-1)]
    swapInds=hInds[:(gt0_MaxI-1)]
    num_add=(len(swapInds)+1)
    #swapIndR=swapInds+(len(swapInds)+1)
    swapIndR=[x+num_add for x in swapInds]
    swapHrev=np.copy(swapHist[::-1])  # not a reference, 
    # ...create blank array of same size as iHist, add reversed histogram
    nHist=np.zeros(len(iHist))
    nHist[gt0_MaxI]=gt0_MaxH
    nHist[swapInds]=iHist[swapInds]
    nHist[swapIndR]=swapHrev  

    # Calculate mean, sd
    nMean=np.sum(nHist*iLocs)/np.sum(nHist)
    nStdv=np.sqrt(np.sum(nHist*(np.square(iLocs-nMean)))/np.sum(nHist))  
    print nMean,nStdv
    # Calculate zScore
    zScore=(cldBand-nMean)/nStdv

    pVal=norm.cdf(zScore) # cumulative distribution function of normal distribution
    pVal=pVal*100

    #print pVal.shape
    cldBand1=pVal
    cldBand1[cldBand1 > 99.95]=0
    cldBand1[cldBand1 != 0]=1
	
  else:
    cldBand1=cldBand
    cldBand1[cldBand1 > 0]=0
    cldBand1[cldBand1 != 0]=1
  
  return cldBand1
  
#######################################################
	
def do_masking(inimg, outimg, outdir, intBN):

  in_ds=gdal.Open(inimg, GA_ReadOnly)

  if in_ds is None:
    print 'Could not open ' + inimg
    sys.exit(1)
  try:
    #with open (inimg+".hdr", "r") as hdrfile1:
    #with open (inimg[:-4]+".hdr", "r") as hdrfile1:
    #  hdr=hdrfile1.read().replace('\r', '').strip()    
    #  hdrinfo= get_envi_header_dict(hdr)  

    
    if (os.path.exists(outimg)):
      print "File exists!"
      in_ds=None   
      sys.exit(1)	 

    hdrinfo=envi_header_handler.ENVI_Header(inimg+".hdr")
    
    interleave=hdrinfo.get_value('interleave')

    remove_hdr_item(hdrinfo,'wavelength units' )
    remove_hdr_item(hdrinfo,'wavelength' )
    remove_hdr_item(hdrinfo,'bbl' )
    remove_hdr_item(hdrinfo,'z plot titles' )
    remove_hdr_item(hdrinfo,'z plot range' )
    remove_hdr_item(hdrinfo,'fwhm' )
    remove_hdr_item(hdrinfo,'default bands' )

    with open(outimg, 'ab') as f:	
	  #GET BACKGROUND MASK AND SET UP SMOOTHING KERNEL

      #b1=in_ds.GetRasterBand(62).ReadAsArray()   # 0.94 micrometer
      ##b1=read_array(in_ds.GetRasterBand(62))  # 0.94 micrometer
      gdaltype=in_ds.GetRasterBand(120).DataType
      nband=in_ds.RasterCount
      #sys.exit(0)
      if interleave=='bip':      
        b1=read_bip2array(inimg,[120],nband,in_ds.RasterYSize,in_ds.RasterXSize,gdaltype)
      if interleave=='bil':      
        b1=read_bil2array(inimg,[120],nband,in_ds.RasterYSize,in_ds.RasterXSize,gdaltype)
      if interleave=='bsq':      
        b1=read_bsq2array(inimg,[120],nband,in_ds.RasterYSize,in_ds.RasterXSize,gdaltype)      
      
      b1=b1[:,:,0]
      bkgMask=np.copy(b1)
      bkgMask[bkgMask >=0]=1
      bkgMask[bkgMask<0]=0

      kernelSize3 = [3, 3] 
      kernel = np.zeros((kernelSize3[0],kernelSize3[1]))+1./((kernelSize3[0]*kernelSize3[1]))  
      
      #CLOUD SHADOW MASKING
      #Fill background 	  
      shdBand=shd_mask(in_ds, b1,bkgMask,kernel,inimg,nband,gdaltype,interleave)
	
	  #CLOUD MASKING
      cldBand=cld_mask(in_ds, b1,shdBand,inimg,nband,gdaltype,interleave)
      #f.write(cldBand.astype(np.float32))
      #sys.exit(0)
      #COMBINE
      allBand=(shdBand*bkgMask*cldBand).astype(np.float16)
      allBand=sig.convolve(allBand,kernel, mode = 'same')  #mean filter
      allBand[allBand < 0.7]=0
      allBand[allBand != 0]=1
      allBand=allBand*bkgMask
      allBand[allBand == 0]=100
      abInd=(allBand != 100)
      abCNT=len(allBand[abInd])
      if (abCNT != 0): 
        allBand[abInd]=0
	  
      #sys.exit(0)
	  
      f.write(allBand.astype(np.uint8))
      f.write(cldBand.astype(np.uint8))
      f.write(shdBand.astype(np.uint8))
      f.write(bkgMask.astype(np.uint8))
      allimg=None
      clsmask=None
      shdBand=None
      bkgMask=None	  

      #hdrinfo['bands']='4'
      #hdrinfo['data type']='1'
      #hdrinfo['band names']=' Land Mask, Cirrus Mask, Low Altitude Cloud Mask, Bad Pixel Mask '
      #write_header_small(outimg[:-4],hdrinfo)	  

      hdrinfo.change_value("bands",'4')
      hdrinfo.change_value("interleave",'bsq')
      hdrinfo.change_value("data type",'1')
      hdrinfo.change_value("band names",['Land Mask', 'Cirrus Mask', 'Low Altitude Cloud Mask', 'Bad Pixel Mask'])
      add_hdr_item(hdrinfo, "band names", ['Land Mask', 'Cirrus Mask', 'Low Altitude Cloud Mask', 'Bad Pixel Mask'], 2)
      hdrinfo.write_header(outdir, intBN+"_CSM.hdr")      
	  
  except RuntimeError, e:
    print e
    sys.exit(1)

  in_ds=None
  
  print 'PROCESS COMPLETE'
  
  
def main(argv):
   inputfile = ''
   demfile = ''
   cloudmaskfile= ''

   parser = argparse.ArgumentParser(description='This code is for cloud masking')
   parser.add_argument('-i','--input', help='Input file name',required=True)
   parser.add_argument('-o','--outdir',help='Output dir', required=True)  #OBS_ORT image

   args = parser.parse_args()
 
   ## show values ##
   print ("Input file: %s" % args.input )
   print ("Output dir: %s" % args.outdir )

   inimg=args.input
   intBN=os.path.basename(inimg)
   outdir=args.outdir
   outimg=outdir+'/'+intBN+'_CSM.img'

   print intBN, outimg

   do_masking(inimg, outimg, outdir, intBN)
	  
if __name__ == "__main__":
   main(sys.argv[1:])
