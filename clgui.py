# -*- coding: utf-8 -*-
"""
Created on Mon Dec 28 12:24:04 2020

@author: priscillababiak
"""

from PyQt5.QtWidgets import QApplication
import sys
from dataManager.loadfiles4CIE import RGBImage

app = QApplication(sys.argv)
RGBImageApp = RGBImage()

sys.exit(app.exec_())