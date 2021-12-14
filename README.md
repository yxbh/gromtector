# gromtector

A real time audio classifier focused on detecting my neighbours and my dog's barks.

## Windows

Few things we need to do setup audio processing on windows.

### PyAudio

For windows, download suitable PyAudio wheel file from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio) and pip install.

### ffmpeg

Go to <https://www.gyan.dev/ffmpeg/builds/> or whereever to get a copy of built ffmpeg binaries.  
Extract them somewhere and add the binary folder to the `PATH` environment variable.
