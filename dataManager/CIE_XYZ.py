# -*- coding: utf-8 -*-
"""
Created on Mon Oct 26 19:19:19 2020

@author: priscillababiak
"""
import pandas as pd 
import numpy as np

def CIElab(spec_illum, illum, cscalar, df_list, x_bar, y_bar, z_bar, calcRGB):
    wavelength = df_list["Wavelength"]

    step_size_data = abs(wavelength[0] - wavelength[1])

    step_size = int(abs(illum["Wavelength"][0]-illum["Wavelength"][1])/step_size_data)

    # trim input data to the range of 380-780nm
    temp_1 = df_list.loc[df_list["Wavelength"]==380].index[0]
    temp_2 = df_list.loc[df_list["Wavelength"]==780].index[0]

    trimmed_data = df_list.iloc[temp_1:temp_2+1,:]
    trimmed_data = trimmed_data[['Wavelength','FT','FR','FA (1-FR-FT)']]
    trimmed_data = trimmed_data.iloc[::step_size] # resize data based on step size
    trimmed_data.reset_index(inplace=True, drop=True) # reset indices

    # trim illum data to the range of 380-780nm
    temp_3 = illum.loc[illum["Wavelength"]==380].index[0]
    temp_4 = illum.loc[illum["Wavelength"]==780].index[0]

    trimmed_illum = illum.iloc[temp_3:temp_4+1,:]
    trimmed_illum.reset_index(inplace=True, drop=True) # reset indices

    #S = trimmed_data["FA (1-FR-FT)"]
    S = trimmed_data["FA (1-FR-FT)"]
    # convert to transmission
    T = 10**(2-(S*cscalar))

    N = sum(y_bar*np.asarray(trimmed_illum[spec_illum])) # normalizing term
    CIE_X = sum(T*x_bar*np.asarray(trimmed_illum[spec_illum]))*(1/N)
    CIE_Y = sum(T*y_bar*np.asarray(trimmed_illum[spec_illum]))*(1/N)
    CIE_Z = sum(T*z_bar*np.asarray(trimmed_illum[spec_illum]))*(1/N)
    
    if calcRGB: # convert X,Y,Z tristimulus values to rgb
        r,g,b = xyz2rbg(CIE_X,CIE_Y,CIE_Z)
    else:
        r = 0
        g = 0
        b = 0

    # find L* a* b*
    # values for Illuminant C
    x_ref = 98.074
    y_ref = 100.0
    z_ref = 118.232

    var_x = CIE_X/x_ref
    var_y = CIE_Y/y_ref
    var_z = CIE_Z/z_ref

    if (var_x > 0.008856): # unless X,Y,Z are very small, calculation uses cube root.  condition defined by CIE lab calculation rules.
        var_x = var_x**(1/3)
    else:
        var_x = (7.787 * var_x) + (16/116)
    
    if (var_y > 0.008856):
        var_y = var_y**(1/3)
    else:
        var_y = (7.787 * var_y) + (16/116)
    
    if (var_z > 0.008856):
        var_z = var_z**(1/3)
    else:
        var_z = (7.787 * var_z) + (16/116)
    
    # calculating L*a*b* from XYZ
    CIE_L = (116*var_y) - 16
    CIE_a = 500 * (var_x - var_y)
    CIE_b = 200 * (var_y - var_z)
    
    return CIE_L,CIE_a,CIE_b,r,g,b

def xyz2rbg(X,Y,Z):
    var_X = X/100
    var_Y = Y/100
    var_Z = Z/100
    
    var_R = var_X * 2.04137 + var_Y * - 0.56495 + var_Z * -0.34469
    var_G = var_X * -0.96927 + var_Y *  1.87601 + var_Z *  0.04156
    var_B = var_X *  0.01345 + var_Y * -0.11839 + var_Z *  1.01541

    var_R_2 = var_R ** ( 1 / 2.19921875 )
    var_G_2 = var_G ** ( 1 / 2.19921875 )
    var_B_2 = var_B ** ( 1 / 2.19921875 )

    aR = var_R_2 * 255
    aG = var_G_2 * 255
    aB = var_B_2 * 255
    
    return aR, aG, aB
    