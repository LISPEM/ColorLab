from SpecEChem_functions import *
from statsmodels.nonparametric.smoothers_lowess import lowess
import pandas as pd
#from sklearn.mixture import GaussianMixture
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# --- User inputs ---
# Automatically load all .txt files in the current folder
file = pd.read_excel(r"XX.xlsx",
                     sheet_name="12chrono2 and 12spec2",
                     skiprows=83, nrows=650, usecols=[13,133])
file = file.rename(columns={351: 'Wavelength', '0.00092.1': 'Absorbance'})
file = file.drop([133,134,303,304,305]).reset_index(drop=True)
x_data = file['Wavelength']
y_data = file['Absorbance']

# Smooth the data
y_smooth_data = lowess(y_data, x_data, frac=0.04, return_sorted=False)

data_start = 0 #180
data_end = len(x_data) #- 60 #435

x = np.zeros(data_end - data_start)
y = np.zeros(data_end - data_start)
y_smooth = np.zeros(data_end - data_start)

for i in range(len(x_data[data_start:data_end])):
    x[i] = x_data[data_start + i]

for i in range(len(x_data[data_start:data_end])):
    y[i] = y_data[data_start + i]

for i in range(len(x_data[data_start:data_end])):
    y_smooth[i] = np.abs(y_smooth_data[data_start + i])

# Find the indices of shoulders
dy_limit = 0.0001
ddy_limit = 0.016*10**-6
i_shoulders = shoulder_idx_find(x, y_smooth, dy_limit, ddy_limit)

# Find the indices of max and min points
w = 1
i_max_min = max_min_find(y_smooth, w)

# Combine arrays into 1
i_features = np.concatenate([i_shoulders, i_max_min])
i_features.sort()

# Remove points that are less than 10 nm away
i_features_remove = []
for i in range(len(i_features)):
    if i == len(i_features) - 1:
        continue
    elif i_features[i+1] - i_features[i] <= 10:
        i_features_remove.append(i+1)

for i in range(len(i_features_remove)):
    i_features = np.delete(i_features,i_features_remove[len(i_features_remove)-1-i])

# Remove points that are within 10 nm from the beginning or end of the data set
if x[len(x) - 1] - x[i_features[len(i_features) - 1]] <= 10:
    i_features = np.delete(i_features, len(i_features) - 1)

if x[i_features[0]] - x[0] <= 10:
    i_features = np.delete(i_features, 0)

detected_peaks = []

for peak in i_features:
    amp = y_smooth[peak]
    mean = x[peak]
    std_dev = 20
    detected_peaks += [amp, mean, std_dev]

lower_bounds = []
upper_bounds = []

for peak in i_features:
    mu = x[peak]
    lower_bounds.extend([0, mu - 10, 5])        # amp ≥ 0, μ ±5 nm, σ ≥ 5
    upper_bounds.extend([np.inf, mu + 10, 35])  # σ capped

opt_params, _ = curve_fit(multi_gaussian,
                          x, y_smooth,
                          p0 = detected_peaks,
                          bounds=(lower_bounds, upper_bounds),
                          maxfev=20000
                          )

plt.figure(figsize=(8, 6))
#plt.plot(x, np.abs(y), zorder = 1)
plt.plot(x, y_smooth, zorder = 1)
plt.scatter(x[i_features], np.abs(y_smooth[i_features]), color='purple', zorder = 2)
plt.plot(x, multi_gaussian(x, *opt_params),
         label='Fitted Curve', linestyle = '--', color = 'red', zorder = 3)

num_peaks = int(len(opt_params) / 3)

for i in range(num_peaks):
    amp, mean, std_dev = opt_params[i * 3 : i * 3 + 3]
    plt.plot(x, gaussian(x, amp, mean, std_dev), label = f'Peak {i+1}')

plt.show()
