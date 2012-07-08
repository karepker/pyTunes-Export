# pyTunes Export

## Synopsis
A utility to export iTunes playlists written in python.

## Usage
pyTunes Export uses Python 3.2. To use pyTunes Export, make sure Python is in your path, cd to the directory of pyTunesExport, and run `python pyTunes_Export`, which will cause pyTunes_Export to launch in interactive mode.

Command line arguments may also be specified for automation. Currently, the following optional arguments are accepted:

`-h, --help`          show help message and exit
`-a, --all`           export all playlists
`-e [EXTENSION [EXTENSION ...]], --extension [EXTENSION [EXTENSION ...]]`
					specify the extension of the playlist in the form
					'wpl' or 'm3u8'
`-p [PLAYLISTS [PLAYLISTS ...]], --playlists [PLAYLISTS [PLAYLISTS ...]]`
					specify the playlists to export
`-f, --file`          export playlists specified in a text file (use the
					settingsfile to specify the location of the text file)
						
The same information may be produced by supplying `-h` or `--help`.

## Features
pyTunes Export currently features the ability to export playlists to Windows media playlist files (.wpl) and M3U files with support for special characters with UTF-8 (m3u8).

## TODO
* Align output in default mode
* Add logging level command line argument 

## Support
Let me know if you have any suggestions for features or run into any issues!

## Credits
pyTunes-Export was inspired by Eric Daugherty's [iTunes Export application](http://www.ericdaugherty.com/dev/itunesexport/) and written by Kar Epker