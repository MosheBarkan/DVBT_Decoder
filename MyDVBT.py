#%matplotlib qt
import ipympl
import Record
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import scipy
import scipy.signal as sig
matplotlib.use('nbagg')
from xml.dom import minidom
import Record
def extractParamsFromXhdr(samples_file_path, xhdr_filename):
    
    header_file = minidom.parse(samples_file_path + xhdr_filename)
    parameters = header_file.getElementsByTagName('capture')
    fs = int(parameters[0].attributes['sample_rate'].value)
    bw = int(parameters[0].attributes['span'].value)
    fc = float(parameters[0].attributes['center_frequency'].value)
    parameters = header_file.getElementsByTagName('data')
    N = int(parameters[0].attributes['samples'].value)
    
    return (fs, N, bw, fc)


def extractSamplesFromXdat(samples_file_path, xdat_filename):
    
    iq_data = np.fromfile(samples_file_path + xdat_filename, dtype='int16')
    iq_data = (iq_data[::2] +1j*iq_data[1::2])
    
    return iq_data

def getSamplesFromRecording(samples_file_path, xdat_filename, xhdr_filename):
    
    (fs, N, bw, fc) = extractParamsFromXhdr(samples_file_path, xhdr_filename)
    iq_data = extractSamplesFromXdat(samples_file_path, xdat_filename)
    
    return (iq_data, fs, N, bw, fc)
    
def saveSamplesToXDAT(data, samples_file_path, xdat_filename, data_type="int16"):
    data.astype(data_type).tofile(samples_file_path + xdat_filename)
    
def plotPSD(data, fs, title="Data"):
    plt.figure()
    plt.title("PSD of {}".format(title))
    plt.psd(data, NFFT=len(data), Fs=fs)
    
    
def plotScatter(dataX, dataY, title="X vs Y"):
    plt.figure()
    plt.title("Scatter of {}".format(title))
    plt.scatter(dataX, dataY)
    
    
def plotStem(data, title="Data"):
    plt.figure()
    plt.title("Stem Plot of {}".format(title))
    plt.stem(data)    
    
    
def plotPlot(data, title="Data"):
    plt.figure()
    plt.title("Plot of {}".format(title))
    plt.plot(data) 
    
    
def printValues(values, *value_names):
    try:
        if len(value_names) == 0:
            i = 1
            for value in values:
                print("Value{} = {}".format(i,value))
                i += 1
        else:
            i = 0
            for value in values:
                print("{} = {}".format(value_names[i],value))
                i += 1
    
    except TypeError:
        if len(value_names) == 0:
            print("Value1 = {}".format(values))

        else:
            print("{} = {}".format(value_names,values))
            
    except IndexError:
        print("Not enough variable names indicated!")
        

def lowPassFilterDVBT(iq_data, fs, ch_bw=7.61e6, transition_bw=5e3, n_taps=5000, get_plot=False):
    lpf = sig.remez(n_taps, [0, ch_bw/2, ch_bw/2 + transition_bw, fs/2], [1,0], Hz=fs)
    filtered_signal = sig.lfilter(lpf, 1.0, iq_data)
    if (get_plot):
        w,h = sig.freqz(lpf)
        plt.figure()
        plt.plot(w*fs*0.5/np.pi, 20*np.log10(abs(h)))
        plt.xscale('log')
        plt.title('Filter Frequency Response')
        plt.xlabel('Frequency')
        plt.ylabel('Amplitude')
        plt.grid(which='both',axis='both')
        plt.show()
    return filtered_signal


def DVBTModeParams(mode, cyclic_prefix):
    """Returns the DVBT signal's parameters based on the mode and cyclic prefix factor.

        Inputs:
        -------
        mode : int
            Possible modes are: 2 (for 2k mode) or 8 (for 8k mode).
        
        cyclic_prefix : int
            Possible factor values are: 4 (for 1/4), 8 (for 1/8), 16 (for 1/16) or 32 (for 1/32).

        Outputs:
        --------
        FFT_len : int
            The length of the FFT - 2048 for 2k mode or 8192 for 8k mode.
        
        K : int
            The number of carriers in the signal in frequency domain without the guardband - 
            1705 for 2k mode and 6817 for 8k mode.
            These carriers include the data carriers, the pilot carriers and the TPS pilot carriers.
            
        CP_len : int
            The number of cyclic prefix bins - equals to the FFT length divided by the cyclic prefix
            factor, rounded down.
        
        data_carriers_per_symbol : int
            The number of data subcarriers in frequency domain - 1512 for 2k mode or 6048 for 8k mode.
        """
    if (mode == 2):
        FFT_len = 2048
        K = 1705
        data_carriers_per_symbol = 1512
    elif (mode == 8):
        FFT_len = 8192
        K = 6817
        data_carriers_per_symbol = 6048
    else:
        raise ValueError("Invalid mode! Possible modes are: 2 (2k mode) or 8 (8k mode)") 
    
    if not (cyclic_prefix == 4 or cyclic_prefix == 8 or cyclic_prefix == 16 or cyclic_prefix == 32):  
        raise ValueError("Invalid cyclic prefix! Possible values are: 4 (1/4), 8 (1/8), 16 (1/16) or 32 (1/32)")
    
    return (FFT_len, K, FFT_len//cyclic_prefix, data_carriers_per_symbol)


def createPRBS(K):
    '''Create PRBS (Pseudo-Random Binary Sequence) for pilot values'''
    init_seq = np.array([1,1,1,1,1,1,1,1,1,1,1])
    PRBS = np.zeros(K)

    for i in range(0,K):
        PRBS[i] = init_seq[10]
        init_seq[10] = np.logical_xor(init_seq[10],init_seq[8])
        init_seq = np.roll(init_seq,1) 
    
    return PRBS


def toggleOFDMSymbolGuardBand(OFDM_symbol_freq_dom, FFT_len, K, add_or_rmv):
    '''add_or_rmv can receive the values:
            ** "add" or "a" to add guard band to the OFDM symbol
            ** "remove" or "rmv" or "r" to remove the guard band from the OFDM symbol '''
    
    guard_band_low_len = int(np.ceil((FFT_len - K)/2))
    guard_band_high_len = int(np.floor((FFT_len - K)/2))
    
    if (add_or_rmv == "add" or add_or_rmv == "a"):
        guard_band_low = np.zeros(guard_band_low_len,dtype = complex)
        guard_band_high = np.zeros(guard_band_high_len,dtype = complex)
        return np.concatenate((guard_band_low, OFDM_symbol_freq_dom, guard_band_high))
    
    elif (add_or_rmv == "rmv" or add_or_rmv == "remove" or add_or_rmv == "r"):
        return OFDM_symbol_freq_dom[guard_band_low_len:FFT_len-guard_band_high_len]
    
    else:
        raise ValueError("Invalid action! Possible actions: 'add' or 'remove'")
        
        
def toggleCyclicPrefix(OFDM_symbol_time_dom, CP_len, add_or_rmv):
    '''add_or_rmv can receive the values:
            ** "add" or "a" to add CP to the OFDM symbol
            ** "remove" or "rmv" or "r" to remove the CP from the OFDM symbol '''
    
    if (add_or_rmv == "add" or add_or_rmv == "a"):
        cp = OFDM_symbol_time_dom[-CP_len:]
        return np.concatenate([cp, OFDM_symbol_time_dom])
    
    elif (add_or_rmv == "rmv" or add_or_rmv == "remove" or add_or_rmv == "r"):
        return OFDM_symbol_time_dom[CP_len:]
    
    else:
        raise ValueError("Invalid action! Possible actions: 'add' or 'remove'")
        
        
def getFreqDomOFDMSymbolsFromTimeDom(FFT_len, K, CP_len, time_synced_orig_sig_with_CP):
    '''Removes CP, converts to frequency domain and removes guard band'''
    
    symbol_len_with_cp = FFT_len + CP_len
    num_symbols_in_signal = len(time_synced_orig_sig_with_CP)//symbol_len_with_cp
    
    orig_sig_TD_no_cp = np.zeros(num_symbols_in_signal*FFT_len, dtype = complex)
    orig_sig_FD = np.zeros(num_symbols_in_signal*FFT_len, dtype = complex)
    orig_sig_FD_no_guardband = np.zeros(num_symbols_in_signal*K, dtype = complex)
    
    for i in range(0,num_symbols_in_signal):
        start = i*FFT_len
        end = (i+1)*FFT_len

        orig_sig_TD_no_cp[start:end] = toggleCyclicPrefix(time_synced_orig_sig_with_CP[i*symbol_len_with_cp:(i+1)*symbol_len_with_cp], CP_len, "rmv")
#         orig_sig_TD_no_cp[start:end] = time_synced_orig_sig_with_CP[i*symbol_len_with_cp+CP_len//2:(i+1)*symbol_len_with_cp-CP_len//2]

        orig_sig_FD[start:end] = np.fft.fftshift(np.fft.fft(orig_sig_TD_no_cp[start:end]))

        orig_sig_FD_no_guardband[i*K:(i+1)*K] = toggleOFDMSymbolGuardBand(orig_sig_FD[start:end], FFT_len, K, "rmv")

    return orig_sig_FD_no_guardband   


def getTimeDomOFDMSymbolsFromFreqDom(FFT_len, K, CP_len, freq_orig_sig_no_guardband):
    '''Adds guard band, converts to time domain and adds CP'''
    
    symbol_len_with_cp = FFT_len + CP_len
    num_symbols_in_signal = len(freq_orig_sig_no_guardband)//K
    
    freq_orig_sig_with_guardband = np.zeros(num_symbols_in_signal*FFT_len, dtype = complex)
    orig_sig_TD_no_cp = np.zeros(num_symbols_in_signal*FFT_len, dtype = complex)
    orig_sig_TD_with_cp = np.zeros(num_symbols_in_signal*symbol_len_with_cp, dtype = complex)
    
    for i in range(0,num_symbols_in_signal):
        start = i*FFT_len
        end = (i+1)*FFT_len

        freq_orig_sig_with_guardband[start:end] = toggleOFDMSymbolGuardBand(freq_orig_sig_no_guardband[i*K:(i+1)*K], FFT_len, K, "add")
        
        orig_sig_TD_no_cp[start:end] = np.fft.ifft(np.fft.fftshift(freq_orig_sig_with_guardband[start:end]))
        
        orig_sig_TD_with_cp[i*symbol_len_with_cp:(i+1)*symbol_len_with_cp] = toggleCyclicPrefix(orig_sig_TD_no_cp[start:end], CP_len, "add")
        

    return orig_sig_TD_with_cp 


def estimateChannelInOFDMSymbol(FFT_len, K, orig_sig_FD_no_guardband, interp_kind='linear'):
    allCarriers = np.arange(K)
    (continuous_pilots_vec, pilot_pos_in_symbol) = createContinuousPilotsSymbol(FFT_len, K, True)
    
    pilots = orig_sig_FD_no_guardband[pilot_pos_in_symbol] 
    Hest_at_pilots = np.divide(pilots, continuous_pilots_vec[pilot_pos_in_symbol]) 
    
    Hest_abs = scipy.interpolate.interp1d(pilot_pos_in_symbol, abs(Hest_at_pilots), kind=interp_kind)(allCarriers)
    Hest_phase = scipy.interpolate.interp1d(pilot_pos_in_symbol, np.angle(Hest_at_pilots), interp_kind)(allCarriers)
    Hest = Hest_abs * np.exp(1j*Hest_phase)

    return Hest


def removeChannelResponse(FFT_len, CP_len, noisy_signal_FD_no_guardband, interp_kind='linear'):

    num_symbols_in_signal = len(noisy_signal_FD_no_guardband)//K

    equalized_signal = np.zeros(len(noisy_signal_FD_no_guardband), dtype = complex)

    for i in range(0,num_symbols_in_signal):
        Hest = estimateChannelInOFDMSymbol(FFT_len, K, noisy_signal_FD_no_guardband[i*K:(i+1)*K])
        equalized_signal[i*K:(i+1)*K] = noisy_signal_FD_no_guardband[i*K:(i+1)*K]/Hest
        
    return equalized_signal


def findN_Peaks(vector, n):
    n_peaks = np.zeros(n)
    for i in range(0,n):
        n_peaks[i] = np.argmax(vector)
        vector[int(n_peaks[i])] = 0
    return n_peaks



def checkAndProcessInputParameters(N, mode, cyclic_prefix):
        
    (FFT_len, K, CP_len, data_carriers_per_symbol) = DVBTModeParams(mode, cyclic_prefix)

    if (N < 30720): # 30720 = number of samples of 3 OFDM symbols ; 3.36 msec = duration of 2 OFDM symbols
        raise ValueError("Acquisition too short - at least 3.36 msec needed")
    
    if (N < 40960): # Check how many symbols are in original signal
        num_symbols_to_correlate = 3
    else:
        num_symbols_to_correlate = 4
    
    return (FFT_len, K, CP_len, data_carriers_per_symbol, num_symbols_to_correlate)
    

def filterAndResampleToDVBT(iq_data, fs, bw):
    
    # Filter Signal
    if (bw > 8e6):
        filtered_signal = lowPassFilterDVBT(iq_data, fs)
    else:
        filtered_signal = iq_data
   
    # Resample
    if (fs == int(64e6/7)):
        return (iq_data, fs, N)
    else:
        #resampled_signal = sig.resample_poly(filtered_signal,int(64e6/7),7*fs)
        factor = int(64e6/7)/fs
        resampled_signal = sig.resample(filtered_signal,int(len(filtered_signal)*factor))
        fs_new = int(64e6/7)
        N_new = len(resampled_signal)
        return (resampled_signal, fs_new, N_new)


def createContinuousPilotsSymbol(K, get_pilot_pos=False):

    PRBS = createPRBS(K)
    
    pilot_pos_in_symbol = np.array([0,    48,   54,   87,   141,  156,  192,  201,  255,  279,  282,  333,  
                                    432,  450,  483,  525,  531,  618,  636,  714,  759,  765,  780,  804,  
                                    873,  888,  918,  939,  942,  969,  984,  1050, 1101, 1107, 1110, 1137, 
                                    1140, 1146, 1206, 1269, 1323, 1377, 1491, 1683, 1704, 1752, 1758, 1791,   
                                    1845, 1860, 1896, 1905, 1959, 1983, 1986, 2037, 2136, 2154, 2187, 2229,    
                                    2235, 2322, 2340, 2418, 2463, 2469, 2484, 2508, 2577, 2592, 2622, 2643,    
                                    2646, 2673, 2688, 2754, 2805, 2811, 2814, 2841, 2844, 2850, 2910, 2973,     
                                    3027, 3081, 3195, 3387, 3408, 3456, 3462, 3495, 3549, 3564, 3600, 3609,    
                                    3663, 3687, 3690, 3741, 3840, 3858, 3891, 3933, 3939, 4026, 4044, 4122,    
                                    4167, 4173, 4188, 4212, 4281, 4296, 4326, 4347, 4350, 4377, 4392, 4458,    
                                    4509, 4515, 4518, 4545, 4548, 4554, 4614, 4677, 4731, 4785, 4899, 5091,    
                                    5112, 5160, 5166, 5199, 5253, 5268, 5304, 5313, 5367, 5391, 5394, 5445,    
                                    5544, 5562, 5595, 5637, 5643, 5730, 5748, 5826, 5871, 5877, 5892, 5916,    
                                    5985, 6000, 6030, 6051, 6054, 6081, 6096, 6162, 6213, 6219, 6222, 6249,    
                                    6252, 6258, 6318, 6381, 6435, 6489, 6603, 6795, 6816])
    
    if (K == 6817):
        continuous_pilots_per_symbol = 177
    else:
        continuous_pilots_per_symbol = 45
    
    continuous_pilots_vec = np.zeros(K,dtype = complex)

    continuous_pilots_vec[0] = 8*(1-2*PRBS[0])/3
    for k in range(1,continuous_pilots_per_symbol):
        continuous_pilots_vec[int(pilot_pos_in_symbol[k])] = 8*(1-2*PRBS[pilot_pos_in_symbol[k]])/3
    
    if (get_pilot_pos):
        return (continuous_pilots_vec, pilot_pos_in_symbol)
    
    return continuous_pilots_vec


def createScatteredPilotsSymbol(K, symbol_index_in_frame, continuous_pilots_vec):
    
    PRBS = createPRBS(K)
    
    scattered_pilots_symbol = np.zeros(K,dtype = complex)
    lm = 3 * np.mod(symbol_index_in_frame, 4)
    
    for s in range(0,((K - lm) // 12)):
        scattered_pilot_pos = lm + 12 * s
        if not(continuous_pilots_vec[scattered_pilot_pos]):
            scattered_pilots_symbol[scattered_pilot_pos] = 8*(1-2*PRBS[scattered_pilot_pos])/3
    
    return scattered_pilots_symbol


def createScatteredPilotsFrame(K, continuous_pilots_vec=np.zeros(1)):
    symbols_per_frame = 68
    
    if (len(continuous_pilots_vec) == 1):
        continuous_pilots_vec = np.zeros(K,dtype = complex)
    
    scattered_pilots_frame = np.zeros(symbols_per_frame*K,dtype = complex)
    
    for i in range(0,symbols_per_frame):
        scattered_pilots_frame[i*K:(i+1)*K] = createScatteredPilotsSymbol(K, i, continuous_pilots_vec)
    
    return scattered_pilots_frame


def createUniqueWordVector(K, pilots_to_include="both"): 
    '''Create a vector of length K in frequency domain containing only the pilot subcarriers (without guard band). 
        The unique word can include only the continuous pilots, only the scattered pilots, or both.'''
    
    if (pilots_to_include == "continuous" or pilots_to_include == "c"):
        return createContinuousPilotsSymbol(K)
    
    elif (pilots_to_include == "scattered" or pilots_to_include == "s"):
        return createScatteredPilotsFrame(K)
    
    elif (pilots_to_include == "both" or pilots_to_include == "b"):
        continuous_pilots_vec = createContinuousPilotsSymbol(K)
        scattered_pilots_frame = createScatteredPilotsFrame(K, continuous_pilots_vec)
        
        for i in range(0, len(scattered_pilots_frame)//K):
            unique_word_frame = scattered_pilots_frame[i*K:(i+1)*K] + continuous_pilots_vec
        
        return unique_word_frame
        
    else:
        raise ValueError("Invalid pilots to include! Possible values: 'continuous', 'scattered' or 'both'")

    
def createUniqueWordTimeDomain(FFT_len, K, pilots_to_include="both", includeCP=False, CP=0):
    '''Create a vector in time domain containing only pilot subcarriers (includes the guard band in frequency domain). 
    
        The unique word can include only the continuous pilots, only the scattered pilots, or both.
    
        The returned vector can be without the cyclic prefix and be of length FFT_len, or it can include the cyclic prefix 
        (in which case the user must enter its length) and thus be of length FFT_len+CP. '''
        
    unique_word_vec_freq_dom = createUniqueWordVector(K, pilots_to_include)   
    
    if includeCP:
        if CP == 0:
            ValueError("Invalid CP value!")
        return (getTimeDomOFDMSymbolsFromFreqDom(FFT_len, K, CP, unique_word_vec_freq_dom),unique_word_vec_freq_dom)
    
    else:
        num_symbols_in_signal = len(unique_word_vec_freq_dom)//K
    
        freq_orig_sig_with_guardband = np.zeros(num_symbols_in_signal*FFT_len, dtype = complex)
        orig_sig_TD_no_cp = np.zeros(num_symbols_in_signal*FFT_len, dtype = complex)

        for i in range(0,num_symbols_in_signal):
            start = i*FFT_len
            end = (i+1)*FFT_len

            freq_orig_sig_with_guardband[start:end] = toggleOFDMSymbolGuardBand(unique_word_vec_freq_dom[i*K:(i+1)*K], FFT_len, K, "add")
            orig_sig_TD_no_cp[start:end] = np.fft.ifft(np.fft.fftshift(freq_orig_sig_with_guardband[start:end]))
        
        return (orig_sig_TD_no_cp, unique_word_vec_freq_dom)

    
def checkDVBTSymbolTimeCorrelation(orig_sig_corr_vec, unique_word_corr_vec, FFT_len, CP, num_symbols_to_correlate, get_plot=False):
    '''Check time correlation between original signal and unique word of continuous pilots.
    
        Inputs:
        -------
        orig_sig_corr_vec : numpy array of complex values
            The original signal suspected of being DVB-T. Its length must be the length of num_symbols_to_correlate
            OFDM symbols in time domain ( len(orig_sig_corr_vec) == num_symbols_to_correlate*(FFT_len+CP) )
                                
        unique_word_corr_vec : numpy array of complex values
            Unique word of only one OFDM symbol in time domain containing only continuous pilots 
            ( len(unique_word_corr_vec) == FFT_len+CP )
        '''
    
    distance_between_peaks = FFT_len + CP
    
    norm_orig_sig = np.linalg.norm(orig_sig_corr_vec)
    norm_unique_word = np.linalg.norm(unique_word_corr_vec)

    time_corr_vec = np.correlate(orig_sig_corr_vec,unique_word_corr_vec)/np.sqrt(norm_unique_word*norm_orig_sig)

    max_time_corr_index_vec = findN_Peaks(np.abs(time_corr_vec),num_symbols_to_correlate)
    max_time_corr_index_vec_sorted = np.sort(max_time_corr_index_vec)
    
    is_corr = True
    
    # Check if there are 4 whole OFDM symbols in the sample:
    for i in range(0,len(max_time_corr_index_vec_sorted)-1):
        is_corr = is_corr and (np.mod(max_time_corr_index_vec_sorted[i+1] - max_time_corr_index_vec_sorted[i],FFT_len+CP) == 0)
        if not is_corr:
            break

    if is_corr==False: # Check if there are 3 whole OFDM symbols in the sample
        is_corr=True
        max_time_corr_index_vec_sorted = np.sort(max_time_corr_index_vec[:-1])
        for i in range(0,len(max_time_corr_index_vec_sorted)-1):
            is_corr = is_corr and (np.mod(max_time_corr_index_vec_sorted[i+1] - max_time_corr_index_vec_sorted[i],FFT_len+CP) == 0)
            if not is_corr:
                break
    
    if get_plot:    
        plt.figure()
        plt.title("Time Correlation for {}k mode, CP of 1/{}".format(FFT_len, int(FFT_len/CP)))
        plt.plot(np.abs(time_corr_vec))
        plt.plot(max_time_corr_index_vec_sorted, np.abs(time_corr_vec[max_time_corr_index_vec_sorted.astype(int)]), "x")
        
    if (is_corr):
        return (is_corr, max_time_corr_index_vec_sorted)
    else:
        return (is_corr, False)

        
def calcDVBTFrequencyShift(FFT_len, K, orig_sig_1symbol_no_cp, unique_word_vec_freq_dom, get_plot=False):

    norm_unique_word_no_cp = np.linalg.norm(unique_word_vec_freq_dom)
    norm_orig_sig = np.linalg.norm(orig_sig_1symbol_no_cp)

    orig_signal_fft_corr_no_cp = np.fft.fftshift(np.fft.fft(orig_sig_1symbol_no_cp))
    unique_word_vec_with_guardband = toggleOFDMSymbolGuardBand(unique_word_vec_freq_dom, FFT_len, K, "add")
    
    freq_corr_vec = np.correlate(orig_signal_fft_corr_no_cp, unique_word_vec_with_guardband, "same")/np.sqrt(norm_unique_word_no_cp*norm_orig_sig)
    
    if get_plot:
        plotPlot(np.abs(freq_corr_vec), "Frequency Correlation")
        
    return np.argmax(np.abs(freq_corr_vec))
        

def getSynchronizedSignal(unsynced_signal_time_dom, fs, time_shift, freq_shift):

    time_synchronized_signal = unsynced_signal_time_dom[time_shift:]
    fc = np.exp(-1.0j * 2.0 * np.pi * freq_shift/fs * np.arange(len(time_synchronized_signal)))

    return time_synchronized_signal * fc


def isDVBTSignal(resampled_signal, fs, bw, N, mode, cyclic_prefix, get_time_corr_plot=False, get_freq_corr_plot=False):
           
    (FFT_len, K, CP, data_carriers_per_symbol, num_symbols_to_correlate) = checkAndProcessInputParameters(N, mode, cyclic_prefix)
    
    (unique_word_vec_time_dom, unique_word_vec_freq_dom) = createUniqueWordTimeDomain(FFT_len, K, "continuous", includeCP=False) 
    
    orig_signal_to_correlate = resampled_signal[0:num_symbols_to_correlate*(FFT_len + CP)]
    

    (is_DVBT, max_time_corr_index_vec) = checkDVBTSymbolTimeCorrelation(orig_signal_to_correlate, unique_word_vec_time_dom, FFT_len, CP, num_symbols_to_correlate, get_plot=get_time_corr_plot)
    
    
    if (is_DVBT):
        time_shift = int(max_time_corr_index_vec[0]) - CP
        if (time_shift < 0):
            time_shift = FFT_len + CP + time_shift
        
        orig_sig_1symbol_no_cp = orig_signal_to_correlate[time_shift+CP:time_shift+FFT_len+CP]
        freq_shift = FFT_len/2 - calcDVBTFrequencyShift(FFT_len, K, orig_sig_1symbol_no_cp, unique_word_vec_freq_dom, get_plot=get_freq_corr_plot)  
        
        synchronized_signal = getSynchronizedSignal(resampled_signal, fs, time_shift, freq_shift)
        
        return (is_DVBT, synchronized_signal)
    
    else:
        return (is_DVBT, False)
    
# Checks for all possible values of FFT mode and cyclic prefix length

def isAnyDVBTSignal(iq_data, fs, bw, N, get_time_corr_plot=False, get_freq_corr_plot=False):
    
    modes = [2, 8]
    cyclic_prefixes = [4, 8, 16, 32]
    
    
    (resampled_signal, fs, N) = filterAndResampleToDVBT(iq_data, fs, bw)
    
    for mode in modes:
        for CP in cyclic_prefixes:
            (is_DVBT, synchronized_signal) = isDVBTSignal(resampled_signal, fs, bw, N, mode, CP, get_time_corr_plot, get_freq_corr_plot)
            if (is_DVBT):
                return (is_DVBT, mode, CP, synchronized_signal)
    
    return (False, 0, 0, False)


#iq_data = Record.parse_xdat('DVB-T_8Mhz2019-05-30_13-32-29.xdat')
#hdr = Record.parse_xhdr('DVB-T_8Mhz2019-05-30_13-32-29.xhdr')
#iq_data = iq_data * hdr.scale
#(resampled_signal, fs, N) = filterAndResampleToDVBT(iq_data, hdr.fs, hdr.fs)
#hdr.fs = fs
#Record.CreateRecord(resampled_signal,'NewXdat',hdr)

#Convert XDAT To cfile
import Record
import numpy as np
iq_data = Record.parse_xdat('Records_xdat\DVB-T_8Mhz2019-05-30_13-32-29.xdat')
att = Record.parse_xhdr('Records_xdat\DVB-T_8Mhz2019-05-30_13-32-29.xhdr')
print('IQ Data and XHDR Load done')
iq_data = iq_data * att.scale
print('Multiplied IQ Data by ScaleFactor')
iq_data = iq_data[0:int(len(iq_data)/10)]
print('Taking 1/10 of the IQ Data and reampling it')
(resampled_signal, fs, N) = filterAndResampleToDVBT(iq_data, att.fs, att.fs)
print('Resampling Done')
#Exporting to CFILE
I = np.real(resampled_signal).astype('float32')
Q = np.imag(resampled_signal).astype('float32')
data_list = []
print('Creating the cfile data as float32s IQIQIQ')
for i in range(len(I)):
    data_list.append(I[i])
    data_list.append(Q[i])
data = np.array(data_list) 
data.astype('float32').tofile('Records_cFile\DVB-T_8Mhz2019-05-30_13-32-29.cfile')
print('Saved as DVB-T_8Mhz2019-05-30_13-32-29.cfile')