# split_audio.py
Split long speech files into chunks with given average duration in conjonction with svc (so-vits-svc-fork)(https://github.com/voicepaw/so-vits-svc-fork)

IMPORTANT NOTE:
For this to work you need to be able run ffmpeg as command from within Python with the subprocess library. 
The command that is executed is : `ffmpeg`
If it doesn't work for you, you'll have to figure out the path to your ffmpeg executable and modify line 24 accordingly in split_audio.py

So, I wanted to share here a tool that you might feel helpful (or not...) 

Consider the following file (librivox):
https://ia801401.us.archive.org/25/items/beckoningfairone_2211_librivox/beckoningfairone_08_onions_128kb.mp3

The file is 30 min and 46 sec.

In order to train a voice, the samples should be less than ~10 sec (cf Notes on https://github.com/voicepaw/so-vits-svc-fork) and typically more than one second.

WHAT DOES IT DO?

A) First, it will apply a loudness normalization to the audio, convert it to 44100 Hz, apply a high-pass filter (>60 Hz), apply a noise gate (to minimize the noise between two sentences), apply a second normalization specific to speech.
Note: You can skip this with the `--no_process True` option 

B) After all this is done, it will:

a) Trim silences. All silences > 0.5 sec will be trimmed down to 0.5 sec (default value). The silence duration as well as the threshold are adjustable but I would advise to keep the default.

b) Split the input file into audio chunks with the desired average duration (the default is 5 seconds) and put them into the output folder located in the same folder as the audio. If the folder doesn't exist it will create it. If it exists, it will delete it and recreate it.
You can specify a minimal duration (default: 2 sec) and a maximal duration (default: 10 sec). 

Let's take an example:

I have the above mentioned mp3 file from librivox in the TEST/ folder
```
python split_audio.py --desired_duration 6 -o my_chunks TEST/beckoningfairone_08_onions_128kb.mp3
```
will convert the mp3 to wav then proceed. 

Here, the histogram of the durations for the input file:

![alt text](https://github.com/sbersier/split_audio/blob/main/audio_split.png?raw=true)

NOTES:

1) If the audio is not in .WAV it will make a .wav copy of the input file next to the original file
2) It assumes that all the relevant audio is contained in one file, say: some_long_audio.mp3
If your audio is scattered among different files, you can concatenate them using ffmpeg or in Audacity.


The resulting audio chunks will be put into the my_chunks folder next to the input file. In the terminal:

```
python split_audio.py --desired_duration 6 -o my_chunks TEST/beckoningfairone_08_onions_128kb.mp3
```
```
Converting to .wav ...
Done.
****************************************************************
Pre-processing ...
Done.
****************************************************************
Processing ...
****************************************************************


Input file:  TEST/beckoningfairone_08_onions_128kb.mp3
----------------------------------------------------------------
Number of audio chunks produced   :    222
Total audio duration [hh:mm:ss]   : 00:22:15
Average audio chunk duration [sec]:   6.01
Durations CFI at 95% CL [sec]     :   1.82
Max audio chunk duration [sec]    :   9.36
Min audio chunk duration [sec]    :   3.26
----------------------------------------------------------------
```

In this case, I asked for 6 seconds chunks (average). The original length of the input file was 30 min and 46 seconds. The resulting audio duration is 22 min 15 sec because long silences were trimmed down to 0.5 sec (the default) "Durations CFI" means, in this case, that 95% of the produced chunks have a duration between 4 and 8 seconds. The max duration is 9.36 sec and the min is 3.26 sec.  (CI="Confidence Interval", CL="Confidence Level") Note: Because there is a minimum and maximum durations specified (by default: 2 sec and 10 sec), it may happen that a bit of is dropped. If you want to keep absolutely everything, you can set the options: --min_duration 0  and --max_duration 9999

I recommend to keep the default options to begin with. 
If don't keep the default threshold and want to set your own, keep an eye on the terminal output. You might see
For the options:
```
python split_audio.py --help
usage: split_audio.py [-h] [-o OUTPUT_FOLDER] [-m MIN_DURATION] [-l MAX_DURATION] [-d DESIRED_DURATION] [-t THRESHOLD] [-s SILENCE] [-v VERBOSE] [-k KEEP] [-n NO_PROCESSING] input_file

positional arguments:
  input_file            input wav audio file

options:
  -h, --help            show this help message and exit
  -o OUTPUT_FOLDER, --output_folder OUTPUT_FOLDER
                        name of output folder (default: processed)
  -m MIN_DURATION, --min_duration MIN_DURATION
                        min duration [sec] (default: 2)
  -l MAX_DURATION, --max_duration MAX_DURATION
                        max duration [sec] (default: 10)
  -d DESIRED_DURATION, --desired_duration DESIRED_DURATION
                        desired average duration [sec] (default: 7)
  -t THRESHOLD, --threshold THRESHOLD
                        silence threshold in dB below max (>0) (default: 35)
  -s SILENCE, --silence SILENCE
                        max silence duration for trimming [sec] (default: 0.5)
  -v VERBOSE, --verbose VERBOSE
                        [true/false] verbose ffmpeg outputs (default: false) (optional)
  -k KEEP, --keep KEEP  [true/false] don't remove temporary files (default: false)
  -n NO_PROCESSING, --no_processing NO_PROCESSING
                        skip pre-processing (default: false)
```


