#!/usr/bin/env python
# coding: utf-8
import librosa
import soundfile as sf
import numpy as np
import os, sys
import glob
import subprocess
import argparse
import time

# split_audio.py uses ffmpeg which must be available from command line
# You migh have to change the ffmpeg_command depending on your platform (?)
# The default is "ffmpeg" (assumes standard ffmpeg installation on Linux)
#    
#
# Example:
# Using default parameters (recommended):
# python split_audio.py path/to/someinput.wav
#
# Will create a folder named (by default) "processed" within the folder containing the audio file.
#
#*************************************************************
ffmpeg_command='ffmpeg' # FFMPEG command (works on Linux)
#*************************************************************


argParser = argparse.ArgumentParser()
argParser.add_argument("input_file", help="input wav audio file", type=str)
argParser.add_argument("-o", "--output_folder", help="name of output folder (default: processed)", type=str,default='processed')
argParser.add_argument("-m", "--min_duration", help="min duration [sec] (default: 2)", type=float, default=2)
argParser.add_argument("-l", "--max_duration", help="max duration [sec] (default: 10)", type=float, default=10)
argParser.add_argument("-d", "--desired_duration", help="desired average duration [sec] (default: 7)", type=float, default=5)
argParser.add_argument("-t", "--threshold", help="silence threshold in dB below max (<0) (default: -35)", type=float, default=-35)
argParser.add_argument("-s", "--silence", help="max silence duration for trimming [sec] (default: 0.5)", type=float,default=0.5)
argParser.add_argument("--keep", dest="keep", help="don\'t remove temporary files",action='store_false', default=True)
argParser.add_argument("--no_processing", dest="no_processing", help="skip PRE-processing",action="store_true")
argParser.set_defaults(no_processing=False)

args = argParser.parse_args()

if not os.path.exists(args.input_file):
    print('ERROR: input_file ',args.input_file, ' doesn\'t exist.')
    sys.exit()


if args.threshold>0:
    print('ERROR: --threshold has to be negative. This is nb. of dB below the maximum.')
    sys.exit()
  
File=args.input_file

if str.upper(File[-4:])!=".WAV":
    print('Converting to .wav ...')
    path=os.sep.join(File.split(os.sep)[0:-1])
    name=File.split(os.sep)[-1:][0].split('.')[0]+'.wav'
    out=path+os.sep+name

    cmd=[ffmpeg_command, '-y', '-i', File,'-q:a','0',  out]
    process = subprocess.run(cmd, capture_output=True)
    print('Done.')
    

keep=args.keep    
outFolder=args.output_folder
inputFolder=os.sep.join(File.split(os.sep)[:-1])+os.sep
outputFolder=inputFolder+outFolder

if outFolder in os.listdir(inputFolder):
    for f in glob.glob(outputFolder+os.sep+'*.wav'):
        os.remove(f)
else:
    os.mkdir(outputFolder)

max_silence=args.silence
desired_duration=args.desired_duration
min_duration=args.min_duration
max_duration=args.max_duration
top_db=args.threshold

if min_duration<0 or max_duration<0 or max_silence<0:
    print('ERROR: Durations [sec] should be positive.')
    sys.exit()
    
if not args.no_processing:
    print('*'*64)
    print('Pre-processing ...')

    # First: loundorm
    cmd=[ffmpeg_command, '-y', '-i', File,'-af','loudnorm=I=-24', 'output.tmp.0.wav']
    process = subprocess.run(cmd, capture_output=True)

    # Resample at 44100 Hz
    cmd=[ffmpeg_command, '-y', '-i', 'output.tmp.0.wav','-ar','44100', 'output.tmp.1.wav']
    process = subprocess.run(cmd, capture_output=True)

    # highpass at 30 Hz to avoied denormalized signals, noise gate with 250ms release, speechnorm
    cmd=[ffmpeg_command, '-y', '-i', 'output.tmp.1.wav', '-af','highpass=f=80,agate=release='+str(max_silence/2*1000)+':threshold=-35dB, speechnorm=e=1.5:r=0.00001:l=1','output.tmp.2.wav']
    process = subprocess.run(cmd, capture_output=True)

    # trim silences
    cmd=[ffmpeg_command, '-y', '-i', 'output.tmp.2.wav', '-af','silenceremove=stop_periods=-1:stop_duration='+str(max_silence)+':stop_threshold=-40dB' ,'output.tmp.3.wav']
    process = subprocess.run(cmd, capture_output=True)

    y, sr = librosa.load('output.tmp.3.wav',sr=None)
    if not keep:
        os.remove('output.tmp.0.wav')
        os.remove('output.tmp.1.wav')
        os.remove('output.tmp.2.wav')
        os.remove('output.tmp.3.wav')
    print('Done.')

else:
    y, sr = librosa.load(File,sr=None)

print('*'*64)
print('Processing ...')
intervals=librosa.effects.split(y,top_db=-top_db)

if len(intervals)<1:
    print('ERROR: librosa couldn\'t detect silence. Possible cause: --threshold is too low')
    sys.exit()
initPoints=np.arange(0, len(y), int(desired_duration*sr))[1:-1]
Points=initPoints

Min=1e10; Max=-1e10
for i in range(len(intervals)):
    d=(intervals[i][1]-intervals[i][0])/sr
    if d<Min:
        Min=d
    if d>Max:
        Max=d
        
Flag=0

if len(intervals)==1 and len(y)/sr>desired_duration:
    print('ERROR: Either desired duration is too large or --threshold is too low')
    sys.exit()

NewIntervals=[]
for i in range(len(intervals)-1):
    if Flag==0 and intervals[i+1][0]-intervals[i][1]<max_silence*sr:
        intervals[i][1]=intervals[i+1][1]
        NewIntervals.append(intervals[i])
        intervals[i+1][0]=intervals[i+1][1]
        Flag=1
    else:
        Flag=0
    i+=1

for i in range(len(Points)):
    Diff=Points[i]-intervals
    d=np.abs(Diff)
    Min=np.min(d)
    ind=np.array(np.where(d==Min)).flatten()
    start, end = intervals[ind][0]
    dd=np.abs(Diff[ind[0]])
    try:
        if abs(dd[0])>=abs(dd[1]):
            Points[i]=(intervals[ind[0]][1]+intervals[ind[0]+1][0])*0.5
        if abs(dd[0])<abs(dd[1]):   
            Points[i]=(intervals[ind[0]][0]+intervals[ind[0]-1][1])*0.5
    except:
        print('ERROR: Threshold is probably to high.')
        sys.exit()

S=np.concatenate((np.array([0]),Points, np.array([len(y)])))

durations=[]
rejected_short=0
rejected_long=0
Nchunks=0
calc_max_duration=-1e10
calc_min_duration=+1e10

for i in range(len(S)-1):
    Nchunks+=1
    start=S[i]
    end=S[i+1]
    duration=(end-start)/sr
            
    if duration > min_duration and duration<max_duration:
        if duration>calc_max_duration:
            calc_max_duration=duration
        if duration<calc_min_duration:
            calc_min_duration=duration
        durations.append((end-start)/sr)
        name=outputFolder+os.sep+str(i).zfill(8)+'.wav'
        
        sf.write(name, y[start:end+1], sr)
    else:        
        if duration>0 and duration<min_duration:   # It may happen that 2 Points collide but it doesn't result in loss of audio
            rejected_short+=1
        if duration>max_duration:
            rejected_long+=1
Nchunks=Nchunks-rejected_short-rejected_long
       
print('*'*64)
print('Input file: ', File)
print('-'*64)
print('Number of audio chunks produced   : ',"{:5}".format(Nchunks))
print('Total audio duration [hh:mm:ss]   :',time.strftime('%H:%M:%S', time.gmtime(np.sum(durations))))
print('Average audio chunk duration [sec]: ',"{:5.2f}".format(np.mean(durations)))
print('Durations CFI at 95% CL [sec]     : ',"{:5.2f}".format(2*np.std(durations)))
print('Max audio chunk duration [sec]    : ',"{:5.2f}".format(calc_max_duration))
print('Min audio chunk duration [sec]    : ',"{:5.2f}".format(calc_min_duration))
if rejected_short>0:
    print('Nb. rejected (duration < min)     : ',"{:5}".format(rejected_short))
if rejected_long>0:
    print('Nb. rejected (duration > max)     : ',"{:5}".format(rejected_long))
print('-'*64)        
print()



