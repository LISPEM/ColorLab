# -*- coding: utf-8 -*-
"""
Created on Mon Sep 28 19:40:09 2020

@author: priscillababiak
"""

import os
import sys
import pandas as pd 
import numpy as np
from dataManager.CIE_XYZ import CIElab
import matplotlib.pyplot as plt
from matplotlib import rcParams
rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Calibri']
rcParams['font.weight'] = 'bold'
rcParams['axes.labelweight'] = 'bold'
rcParams['savefig.dpi'] = 300
from PyQt5.QtWidgets import QMainWindow, QFileDialog
from ui.cl import Ui_MainWindow

illum = pd.read_excel(r'dataManager/illuminants.xls')

class RGBImage(QMainWindow): 
    
    def __init__(self) -> None:
        super().__init__()
        self.gui = Ui_MainWindow()
        self.gui.setupUi(self)
        self.gui.pushButton.clicked.connect(self.click)
        self.gui.pushButton_2.clicked.connect(self.loadFiles)
        self.show()
        
    def click(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        self.filepath = QFileDialog.getExistingDirectory(self,"Select File Directory")
        self.gui.lineEdit.setText(self.filepath)
        self.gui.lineEdit.setReadOnly(False)
        
    def loadFiles(self):
        
        self.statusBar().clearMessage()
        filelist = os.listdir(self.filepath)
        filelist.sort()
        spec_illum = str(self.gui.comboBox.currentText()) # specify the illuminant
        cscalar =  int(self.gui.comboBox_2.currentText()) # specify saturation scalar
        image_title = str(self.gui.lineEdit_2.text())
        image_aspect = float(self.gui.lineEdit_3.text())
        calc_rgb = True # do you want to calculate rgb values?

        # xyz bar values for illuminant
        x_bar = [0.001368,0.002236,0.004243,0.00765,0.01431,0.02319,0.04351,0.07763,0.13438,0.21477,0.2839,0.3285, \
                 0.34828,0.34806,0.3362,0.3187,0.2908,0.2511,0.19536,0.1421,0.09564,0.05795,0.03201,0.0147,0.0049, \
                 0.0024,0.0093,0.0291,0.06327,0.1096,0.1655,0.22575,0.2904,0.3597,0.43345,0.51205,0.5945,0.6784, \
                 0.7621,0.8425,0.9163,0.9786,1.0263,1.0567,1.0622,1.0456,1.0026,0.9384,0.85445,0.7514,0.6424,0.5419, \
                 0.4479,0.3608,0.2835,0.2187,0.1649,0.1212,0.0874,0.0636,0.04677,0.0329,0.0227,0.01584,0.011359, \
                 0.008111,0.00579,0.004109,0.002899,0.002049,0.00144,0.001,0.00069,0.000476,0.000332,0.000235,0.000166, \
                 0.000117,8.3e-05,5.9e-05,4.2e-05]
        
        y_bar= [3.9e-05,6.4e-05,0.00012,0.000217,0.000396,0.00064,0.00121,0.00218,0.004,0.0073,0.0116,0.01684,0.023, \
                0.0298,0.038,0.048,0.06,0.0739,0.09098,0.1126,0.13902,0.1693,0.20802,0.2586,0.323,0.4073,0.503,0.6082,\
                0.71,0.7932,0.862,0.91485,0.954,0.9803,0.99495,1,0.995,0.9786,0.952,0.9154,0.87,0.8163,0.757,0.6949, \
                0.631,0.5668,0.503,0.4412,0.381,0.321,0.265,0.217,0.175,0.1382,0.107,0.0816,0.061,0.04458,0.032,0.0232, \
                0.017,0.01192,0.00821,0.005723,0.004102,0.002929,0.002091,0.001484,0.001047,0.00074,0.00052,0.000361, \
                0.000249,0.000172,0.00012,8.5e-05,6e-05,4.2e-05,3e-05,2.1e-05,1.5e-05]
        			
        z_bar = [0.00645,0.01055,0.02005,0.03621,0.06785,0.1102,0.2074,0.3713,0.6456,1.03905,1.3856,1.62296,1.74706,1.7826, \
                 1.77211,1.7441,1.6692,1.5281,1.28764,1.0419,0.81295,0.6162,0.46518,0.3533,0.272,0.2123,0.1582,0.1117, \
                 0.07825,0.05725,0.04216,0.02984,0.0203,0.0134,0.00875,0.00575,0.0039,0.00275,0.0021,0.0018,0.00165,0.0014, \
                 0.0011,0.001,0.0008,0.0006,0.00034,0.00024,0.00019,0.0001,5e-05,3e-05,2e-05,1e-05,0,0,0,0,0,0,0,0,0,0,0,0,0, \
                 0,0,0,0,0,0,0,0,0,0,0,0,0,0]

        num_files = len(filelist)

        lab_values = np.zeros((num_files,6))
        delta = np.zeros((1,num_files))
        i = 0

        # pull first timestamp
        first_time = filelist[0].split('_')[-1]
        first_t = [int(word) for word in first_time.split('.') if word.isdigit()]
        
        # check that image title name is valid
        #re1 =  re.compile(r"^[^<>/{}[\]~`]*$")
        chars_to_be_removed = r'^[^<>/{}[\]~`]*$&#@!;,:'
        filtered_chars = filter(lambda item: item not in chars_to_be_removed, image_title)
        image_name = ''.join(filtered_chars)
        image_name = r'images/' + image_name + '.png'
        # if re1.match(image_title):
        #     print ("Image name is valid!")
        #     image_name = r'images/' + image_name + '.png'
        # else:
        #     error_msg = 'Image name is invalid.  Please rename your file.'
        #     print(error_msg)
        #     sys.exit()

        for file in filelist:
            
            #check if the file is a file, or a directory
            base_dir = self.filepath
            file_name = file
            full_path = os.path.join(base_dir, file_name)
            isdir = os.path.isdir(full_path)
            if isdir:
                print('Skipping ',file,' it is a directory!')
                continue
            else:
                if file.endswith('.csv'):
                    try:
                        uvvis_data = pd.read_csv(r"{0}/{1}".format(self.filepath,file))
                    except:
                        print(file + ' is corrupt!')
                        
                        if file==filelist[-1]:
                            print('***************************')
                            print('All files are corrupt!')
                            print('***************************')
                            sys.exit(0)
                        else:
                            continue
                    
                else:
                    try:
                        uvvis_data = pd.read_table(r"{0}/{1}".format(self.filepath,file))
                    except:
                        print(file + ' is corrupt!')
                        
                        if file==filelist[-1]:
                            print('***************************')
                            print('All files are corrupt!')
                            print('***************************')
                            sys.exit(0)
                        else:
                            continue
                    
                check_data = len(uvvis_data)
                
                if check_data == 0:
                    continue
                
                try:
                    L,a,b,rr,gg,bb = CIElab(spec_illum,illum,cscalar,uvvis_data,x_bar,y_bar,z_bar,calc_rgb)
                    lab_values[i,0] = L
                    lab_values[i,1] = a
                    lab_values[i,2] = b
                    lab_values[i,3] = rr
                    lab_values[i,4] = gg
                    lab_values[i,5] = bb
                    
                    # extract timestamp
                    curr_time = file.split('_')[-1]
                    curr_t = [int(word) for word in curr_time.split('.') if word.isdigit()]
    
                    if curr_t[0] > 3660:
                        seconds_convert = 3600
                        units = 'Hours'
                    else:
                        seconds_convert = 60
                        units = 'Minutes'
                                
                    delta[0,i] = (curr_t[0] - first_t[0])/seconds_convert
    
                    i += 1 # end for loop
                except:
                    print('***********************************************************')
                    print('Could not convert data in ' + file)
                    print('***********************************************************')
                    
                    if file==filelist[-1]:
                        sys.exit(0)

        # remove rows that were not filled
        lab_values =  lab_values[~np.all(lab_values == 0, axis=1)]
        new_num_files = len(lab_values)
        
        if new_num_files == 1:
            # generate image from the degradation data
            scalar = 1
            newdim = scalar*new_num_files
            n = 0
        
            colormat = np.zeros([newdim,newdim,3], dtype=np.uint16)
            for i in range(new_num_files):
                colormat[:,n:n+scalar] = lab_values[i,3:]
                n += scalar
        else:
        
            if seconds_convert == 3600: delta = delta*60
        
            # define the size of the matrix
            delta_delta = np.around(np.diff(delta))
            first_t = 1
        
            temp_dim = int(np.sum(delta_delta))
            colormat = np.zeros((temp_dim,temp_dim,3), dtype=np.uint8)
            for i in range(new_num_files-1):
                for k in range(int(delta_delta[0,i])):
                    if first_t:
                        colormat[:,i+k] = lab_values[i,3:]
                        curr_idx = i+k
                        first_t = 0
                    else:
                        curr_idx = curr_idx+1
                        colormat[:,curr_idx] = lab_values[i,3:]
                
            # resize array
            colormat = colormat[0:curr_idx+1,0:curr_idx+1,:]
            
        len_colormat = len(colormat)

        # general matplotlib settings
        plt.rc('font', size=20)
        # Plotting options can be changed here SY
        if (len_colormat > 1):
            fig, ax = plt.subplots(1,1, figsize=(11,7))
            # figure out axis ticks
            # f_idx = new_num_files*0
            # s_idx = round(new_num_files*0.33)
            # t_idx = round(new_num_files*0.66)
            # l_idx = new_num_files-1
            # ax.set_xticks([f_idx,s_idx,t_idx,l_idx])
            # label_list = [str(round(delta[0,f_idx])),str(round(delta[0,s_idx])),
            #                    str(round(delta[0,t_idx])),str(round(delta[0,l_idx]))]
            # ax.set_xticklabels(label_list)
            if seconds_convert == 3600:
                ax.imshow(colormat,extent=[delta[0,0],np.max(delta)/60,delta[0,0],np.max(delta)/60],
                      aspect='auto')
            else:
                ax.imshow(colormat,extent=[delta[0,0],np.max(delta),delta[0,0],np.max(delta)],
                      aspect='auto')
            ax.axes.get_yaxis().set_visible(False)
            ax.set_xlabel(units)

            for axis in ['top', 'bottom', 'right', 'left']:
                ax.spines[axis].set_linewidth(2)
            ax.tick_params(length=10, width=2, pad=5)
            # ax.set_title(image_title)
            plt.tight_layout()
            fig.savefig(image_name)
        else:
            fig, ax = plt.subplots(1,1)
            ax.imshow(colormat,aspect=image_aspect)
            ax.axes.get_xaxis().set_visible(False)
            ax.axes.get_yaxis().set_visible(False)
            # ax.set_title(image_title)
            for axis in ['top', 'bottom', 'right', 'left']:
                ax.spines[axis].set_linewidth(2)
            ax.tick_params(length=10, width=2, pad=5)
            plt.tight_layout()
            fig.savefig(image_name)
        
        
        self.gui.statusbar.showMessage("Finished!")
        
