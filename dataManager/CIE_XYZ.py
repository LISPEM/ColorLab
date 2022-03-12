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
    # S = trimmed_data["FA (1-FR-FT)"]
    # convert to transmission
    # T = 10**(2-(S*cscalar))
    T = trimmed_data["FT"]
    T = (1+T)



    # N = sum(y_bar*np.asarray(trimmed_illum[spec_illum])) # normalizing term
    # CIE_X = sum(T*x_bar*np.asarray(trimmed_illum[spec_illum]))*(1/N)
    # CIE_Y = sum(T*y_bar*np.asarray(trimmed_illum[spec_illum]))*(1/N)
    # CIE_Z = sum(T*z_bar*np.asarray(trimmed_illum[spec_illum]))*(1/N)

    K = 1 / sum(y_bar*np.asarray(trimmed_illum[spec_illum])) # normalizing term
    CIE_X = sum(T*x_bar*np.asarray(trimmed_illum[spec_illum])) * (K)
    CIE_Y = sum(T*y_bar*np.asarray(trimmed_illum[spec_illum])) * (K)
    CIE_Z = sum(T*z_bar*np.asarray(trimmed_illum[spec_illum])) * (K)


    print("CIE XYZ:", CIE_X, CIE_Y, CIE_Z)
    
    if calcRGB: # convert X,Y,Z tristimulus values to rgb
        r,g,b = xyz2rbg(spec_illum,CIE_X,CIE_Y,CIE_Z)
    else:
        r = 0
        g = 0
        b = 0

    #depreciated, too lazy to get rid of these vestigial variables.
    CIE_L = 0
    CIE_a = 0
    CIE_b = 0
    
    return CIE_L,CIE_a,CIE_b,r,g,b

def xyz2rbg(spec_illum,X,Y,Z):
    

    # sRGB 
    def sRGB(X, Y, Z):
        R = (X * 3.2410) + (Y * -1.5374) + (Z * -0.4986)
        G = (X * -0.9692) + (Y * 1.8760) + (Z * 0.0416)
        B = (X * 0.0556) + (Y * -0.2040) + (Z * 1.0570)

        

        def gamma_adj(C):
            if C < 0.0031308:
                return 12.92 * C
            else:
                return (1.055 * (C**0.41666)-0.055)

        maxVal = max(R,G,B)

        R = gamma_adj(R)
        G = gamma_adj(G)
        B = gamma_adj(B)

        return R, G, B


    def adobeRGB(X,Y,Z):
        print("in the works")
        

    R, G, B = sRGB(X, Y, Z)
    print("post gamma RGB", R, G, B)

    # sRGB conversion
    r = round(R * 255, 0)
    g = round(G * 255, 0)
    b = round(B * 255, 0)

    print(r,g,b)
    
    return r, g, b
    