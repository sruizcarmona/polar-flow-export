mytcx = 'perc/PERCEIVE_2311_2024-01-02_09-44-56.TCX'
mycsv = 'perc/PERCEIVE_2311_2024-01-02_09-44-56.CSV'

import pandas

# read csv file, only the headers and the first row
df = pandas.read_csv(mycsv, nrows=1)

# get value for column 'Sport'
sport = df['Sport'][0]

# change name of tcx to include sport
new_tcx = mytcx.replace('.TCX', '_SPORT_%s.TCX' % sport)

# change file name of tcx file
import os
os.rename(mytcx, new_tcx)

# remove csv file
os.remove(mycsv)