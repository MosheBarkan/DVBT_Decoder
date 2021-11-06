# -*- coding: utf-8 -*-
import lxml.etree as ET
from scipy import signal
import numpy as np

class Attributes:
    def __init__(self,fc,fs,scale):
        self.fc = fc
        self.fs = fs
        self.ts = 1/fs
        self.scale = scale
        
        

def parse_xdat(xdat_filename):
    data = np.fromfile(xdat_filename, dtype='int16')
    data = data.reshape(int(len(data)/2),2)
    I = data[:,0]
    Q = data[:,1]
    return (I + 1j * Q)
    

def parse_xhdr(xhdr_filename):
    try:
        try:
            xhdr = ET.parse(xhdr_filename).getroot()
        except:
            print('Error - invalid XHDR file')
            return 0
        fc = float(xhdr[0][0].attrib['center_frequency'])
        fs = float(xhdr[0][0].attrib['sample_rate'])
        scale = np.power(2,16) * float(xhdr[0][0].attrib['acq_scale_factor'])
        prop = Attributes(fc,fs,scale)
        return prop
    except:
        print('Error - invalid XHDR properites')
        return 0
    
    
def CreateRecord(IQData,Filename,Attributes):
    ##XDAT
    reverse = np.array([np.real(IQData),np.imag(IQData)],dtype='int16')
    reverse = reverse.reshape(1,len(IQData)*2,order='f')
    reverse.astype('int16').tofile(Filename+".xdat")
    
    ##XHDR
    root = ET.Element("xcom_header")
    root.set('header_version','1.0')
    root.set('sw_version','1.1.0.0')
    root.set('name',Filename)
    
    captures = ET.SubElement(root, "captures")
    data_files = ET.SubElement(root, "data_files")
    
    ET.SubElement(captures, "capture",
                  name= Filename,
                  center_frequency=str(Attributes.fc),
                  sample_rate=str(Attributes.fs),
                  span=str(Attributes.fs),
                  acq_scale_factor= str(float(Attributes.scale)/np.power(2,16)))

    ET.SubElement(data_files, "data",
                  channel_count="1",
                  data_encoding="int16",
                  iq_interleave="true",
                  little_endian="true",
                  name= Filename + ".xdat",
                  protected="false",
                  sample_resolution="16",
                  samples= str(int(len(IQData))),
                  signed_type="true")

    tree = ET.ElementTree(root)
    xml_object = ET.tostring(tree,
                             pretty_print=True,
                             xml_declaration=True,
                             encoding='UTF-8')

    with open(Filename +".xhdr", "wb") as writter:
        writter.write(xml_object)
        
        
        
        
def FM_IQ_Demod(IQData):
    b = signal.firls(29,[0,0.9],[0,1])
    d = IQData/np.abs(IQData) #normalize the amplitude
    iData = np.real(d)
    qData = np.imag(d)
    
    FM_demodulated = (qData*signal.convolve(iData,b,'same')-iData*signal.convolve(qData,b,'same'))/(np.power(qData,2)+np.power(iData,2))
    return FM_demodulated