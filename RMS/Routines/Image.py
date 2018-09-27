""" Image processing routines. """

from __future__ import print_function, division, absolute_import

import os

import numpy as np
import scipy.misc



@np.vectorize
def gammaCorrection(intensity, gamma, bp=0, wp=255):
    """ Correct the given intensity for gamma. 
        
    Arguments:
        intensity: [int] Pixel intensity
        gamma: [float] Gamma.

    Keyword arguments:
        bp: [int] Black point.
        wp: [int] White point.

    Return:
        [float] Gamma corrected image intensity.
    """

    if intensity < 0:
        intensity = 0

    x = (intensity - bp)/(wp - bp)

    if x > 0:

        # Compute the corrected intensity
        return bp + (wp - bp)*(x**(1.0/gamma))

    else:
        return bp



def applyBrightnessAndContrast(img, brightness, contrast):
    """ Applies brightness and contrast corrections to the image. 
    
    Arguments:
        img: [2D ndarray] Image array.
        brightness: [int] A number in the range -255 to 255.
        contrast: [float] A number in the range -255 to 255.

    Return:
        img: [2D ndarray] Image array with the brightness applied.
    """

    contrast = float(contrast)

    # Compute the contrast factor
    f = (259.0*(contrast + 255.0))/(255*(259 - contrast))

    img_type = img.dtype

    # Convert image to float
    img = img.astype(np.float)

    # Apply brightness
    img = img + brightness

    # Apply contrast
    img = f*(img - 128.0) + 128.0

    # Clip the values to 0-255 range
    img = np.clip(img, 0, 255)

    # Preserve image type
    img = img.astype(img_type)

    return img 



def adjustLevels(img_array, minv, gamma, maxv, nbits=8):
    """ Adjusts levels on image with given parameters.

    Arguments:
        img_array: [ndarray] Input image array.
        minv: [int] Minimum level.
        gamma: [float] gamma value
        Mmaxv: [int] maximum level.

    Keyword arguments:
        nbits: [int] Image bit depth.

    Return:
        [ndarray] Image with adjusted levels.

    """

    # Calculate maximum image level
    max_lvl = 2**nbits - 1.0

    # Check that the image adjustment values are in fact given
    if (minv == None) and (gamma == None) and (maxv == None):
        return img_array

    minv = minv/max_lvl
    maxv = maxv/max_lvl
    interval = maxv - minv
    invgamma = 1.0/gamma

    img_array = img_array.astype(np.float64)

    # Reduce array to 0-1 values
    img_array = np.divide(img_array, max_lvl)

    # Calculate new levels
    img_array = np.divide((img_array - minv), interval)
    img_array = np.power(img_array, invgamma)

    img_array = np.multiply(img_array, max_lvl)

    # Convert back to 0-255 values
    img_array = np.clip(img_array, 0, max_lvl)

    # WARNING: This limits the number of image levels to 256!
    img_array = img_array.astype(np.uint8)

    return img_array




class FlatStruct(object):
    def __init__(self, flat_img, flat_avg):
        """ Structure containing the flat field.

        Arguments:
            flat_img: [ndarray] Flat field.
            flat_avg: [float] Average value of the flat field.

        """

        self.flat_img = flat_img
        self.flat_avg = flat_avg



def loadFlat(dir_path, file_name):
    """ Load the flat field image. 

    Arguments:
        dir_path: [str] Directory where the flat image is.
        file_name: [str] Name of the flat field file.

    Return:
        flat_struct: [Flat struct] Structure containing the flat field info.
    """

    # Load the flat image
    flat_img = scipy.misc.imread(os.path.join(dir_path, file_name))

    # Convert the flat to float64
    flat_img = flat_img.astype(np.float64)

    # Calculate the median of the flat
    flat_avg = np.median(flat_img)

    # Make sure there are no values close to 0, as images are divided by flats
    flat_img[flat_img < flat_avg/2] = flat_avg

    # Init a new Flat structure
    flat_struct = FlatStruct(flat_img, flat_avg)

    return flat_struct





def applyFlat(img, flat_struct):
    """ Apply a flat field to the image.

    Arguments:
        img: [ndarray] Image to flat field.
        flat_struct: [Flat struct] Structure containing the flat field.
        

    Return:
        [ndarray] Flat corrected image.

    """

    # Check that the input image and the flat have the same dimensions, otherwise do not apply it
    if img.shape != flat_struct.flat_img.shape:
        return img

    input_type = img.dtype

    # Apply the flat
    img = flat_struct.flat_avg*img.astype(np.float64)/flat_struct.flat_img

    # Limit the image values to image type range
    dtype_info = np.iinfo(input_type)
    img = np.clip(img, dtype_info.min, dtype_info.max)

    # Make sure the output array is the same as the input type
    img = img.astype(input_type)

    return img


def deinterlaceOdd(img):
    """ Deinterlaces the numpy array image by duplicating the odd frame. 
    """
    
    # Deepcopy img to new array
    deinterlaced_image = np.copy(img) 

    deinterlaced_image[1::2, :] = deinterlaced_image[:-1:2, :]

    # Move the image one row up
    deinterlaced_image[:-1, :] = deinterlaced_image[1:, :]
    deinterlaced_image[-1, :] = 0

    return deinterlaced_image



def deinterlaceEven(img):
    """ Deinterlaces the numpy array image by duplicating the even frame. 
    """
    
    # Deepcopy img to new array
    deinterlaced_image = np.copy(img)

    deinterlaced_image[:-1:2, :] = deinterlaced_image[1::2, :]

    return deinterlaced_image



def blendLighten(arr1, arr2):
    """ Blends two image array with lighen method (only takes the lighter pixel on each spot).
    """
    arr1 = arr1.astype(np.int16)

    temp = arr1 - arr2
    temp[temp > 0] = 0

    new_arr = arr1 - temp
    new_arr = new_arr.astype(np.uint8)

    return  new_arr




def deinterlaceBlend(img):
    """ Deinterlaces the image by making an odd and even frame, then blends them by lighten method.
    """

    img_odd_d = deinterlaceOdd(img)
    img_even = deinterlaceEven(img)

    proc_img = blendLighten(img_odd_d, img_even)

    return proc_img




if __name__ == "__main__":

    import time

    import matplotlib.pyplot as plt

    from RMS.Formats import FFfile
    import RMS.ConfigReader as cr


    # Load config file
    config = cr.parse(".config")

    # Generate image data
    img_data = np.zeros(shape=(256, 256))
    for i in range(256):
        img_data[:, i] += i


    plt.imshow(img_data, cmap='gray')
    plt.show()

    # Adjust levels
    img_data = adjustLevels(img_data, 100, 1.2, 240)

    plt.imshow(img_data, cmap='gray')
    plt.show()



    #### Apply the flat

    # Load an FF file
    dir_path = "/home/dvida/Dropbox/Apps/Elginfield RPi RMS data/ArchivedFiles/CA0001_20171018_230520_894458_detected"
    file_name = "FF_CA0001_20171019_092744_161_1118976.fits"

    ff = FFfile.read(dir_path, file_name)

    # Load the flat
    flat_struct = loadFlat(os.getcwd(), config.flat_file)


    t1 = time.clock()

    # Apply the flat
    img = applyFlat(ff.maxpixel, flat_struct)

    print('Flat time:', time.clock() - t1)

    plt.imshow(img, cmap='gray', vmin=0, vmax=255)
    plt.show()
