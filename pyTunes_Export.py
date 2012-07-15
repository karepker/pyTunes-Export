import os, sys, argparse, codecs
from xml.dom.minidom import parse
from urllib.parse import unquote
from platform import system
from re import search, sub
from tkinter import Tk
from tkinter.filedialog import askopenfilename, askdirectory

##################################################################
## CONSTANTS
##################################################################

DEBUG = False
SETTINGS_NAME = "settings" # name for the settings file
DEFAULT_FORMAT = "M3U8" # default format to export playlists in

TAB_SIZE = 4 # number of spaces in a tab
TABLE_WIDTH = 50 # width of table used to print playlists

##################################################################
## CLASSES
##################################################################
class iTunes_Library_Parser():

    def __init__(self, xml_file, document = None):
        self.xml_file = xml_file
        self.document = document
        if self.document is None:
            print("Parsing iTunes Library xml file ...", end = " ")
            self.document = parse(self.xml_file)
            print("Done!")
        self.FIRST_TRACK_DICT = 3
        self.TRACK_DICT_SKIP = 4
        self.TRACK_DICT_ID = 2

    def __str__(self):
        return "iTunes Library located at " + str(self.xml_file)

    def get_key(self, node, key_name):
        """return a node of tag name "key" with given name if it exists, else returns None"""
        
        keys = node.getElementsByTagName("key")
        for key in keys:
            if key.nodeType == key.ELEMENT_NODE:
                # return the first key with the specified name found
                if key.childNodes[0].nodeValue == key_name:
                    return key
        return None

    def get_tracks_node(self):
        """Returns the <dict> node containing all of the track information"""

        tracks_key = self.get_key(self.document, "Tracks")
        return tracks_key.nextSibling.nextSibling

    def get_track_dicts(self):
        """Returns a list of <dict>s for each track in the library"""

        # set initial variables
        root_dict = self.get_tracks_node()
        track_dicts = []
        tracks_left = True
        index = 1

        # while there are tracks left
        while tracks_left:

            # try to get the corresponding child node to the index
            try:
                track_dict = root_dict.childNodes[self.FIRST_TRACK_DICT +
                                                  self.TRACK_DICT_SKIP * index]

            # if the index doesn't exist, there are no more tracks, quit the loop
            except IndexError:
                tracks_left = False
                break

            # add the track to the list, increment the index
            else:
                track_dicts.append(track_dict)
                index += 1

        return track_dicts
                
        
    def get_key_value(self, node, to_find):
        """Finds the value of the key given if the key exists, otherwise returns None"""
        key = None
        key_node = self.get_key(node, to_find)
        if key_node is not None:
            key = key_node.nextSibling.childNodes[0].nodeValue
        return key

    def get_key_bool_value(self, node, to_find):
        """Finds the boolean value of the key given if the key exists, otherwise returns None"""
        key = None
        key_node = self.get_key(node, to_find)
        if key_node is not None:
            key = key_node.nextSibling.nodeName
        return key

    def get_track_info(self, track_dict):
        """Returns a string with the location on disk of a track with the given ID"""
        
        info = {}
        
        # get and process the length by getting windows path and removing percent encoding
        raw = self.get_key_value(track_dict, "Location")
        trimmed = search(r"[A-Z]:.*", raw)
        info['location'] = normalize_path(unquote(trimmed.group(0)))

        # get and process the total time in seconds
        milliseconds = self.get_key_value(track_dict, "Total Time")
        info['length'] = int(milliseconds)/1000

        # get and process song and artist name
        info['name'] = self.get_key_value(track_dict, "Name")
        info['artist'] = self.get_key_value(track_dict, "Artist")

        return info
            

class Playlist_Parser(iTunes_Library_Parser):
    """Contains relevant information and method for a playlist"""

    def __init__(self, node, xml_file, document = None):
        self.node = node
        super().__init__(xml_file, document)

    def get_track_ids(self):
        """Returns an array of all the items in the playlist node"""

        # variable initialization
        array = None
        items = []

        # find the tag in the playlist named array
        arrays = self.node.getElementsByTagName("array")

        # if the tag doesn't exist, return an empty list of items
        try:
            array = arrays[0]
        except IndexError:
            return []

        # loop the <dict>s containing Track IDs, add the Track IDs to items list
        current_dict = array.childNodes[0].nextSibling
        while current_dict is not None:
            track_id = int(current_dict.childNodes[0].nextSibling.nextSibling.childNodes[0].nodeValue)
            items.append(track_id)
            current_dict = current_dict.nextSibling.nextSibling

        return items

    def get_tracks_info(self, track_ids = None):
        """Gets the locations on disk of the songs with the given track IDs"""

        # initialize tracks as an empty list
        tracks = []

        # get track ids if not given
        if track_ids is None:
            track_ids = self.get_track_ids()

        track_dicts = self.get_track_dicts()

        for track_dict in track_dicts:

            # get the track_id from the dict
            track_id = int(track_dict.childNodes[self.TRACK_DICT_ID].childNodes[0].nodeValue)

            # if track_id is in the list of track_ids
            # get the info of the track and remove the id from the list 
            if track_id in track_ids:
                if DEBUG:
                    print("Found id " + str(track_id))
                info = self.get_track_info(track_dict)
                tracks.append(info)
                track_ids.remove(track_id)

        # all remaining ids in the list of track ids could not be found
        for remaining in track_ids:
            sys.stderr.write("Could not find track with ID " + str(remaining) + "!\n")

        return tracks
        

class Playlist():
    """Information about a playlist"""

    def __init__(self, playlists_node, xml_file, document = None):
        self.parser = Playlist_Parser(playlists_node, xml_file, document)

    def __str__(self):
        return self.name

    def set_name(self):
        """Sets the value of self.name by finding the value of "Name" in the XML"""
        self.name = self.parser.get_key_value(self.parser.node, "Name")

    def set_persistent_ID(self):
        """Sets the value of self.persistent_ID by finding the value of "Playlist Persistent ID" in the XML"""
        self.persistent_ID = self.parser.get_key_value(self.parser.node, "Playlist Persistent ID")

    def set_parent_ID(self):
        """Sets the value of self.parent_ID by finding the value of "Parent Persistent ID" in the XML"""
        self.parent_ID = self.parser.get_key_value(self.parser.node, "Parent Persistent ID")

    def set_is_folder(self):
        """Sets the value of self.is_folder by finding the boolean value of "Folder" in the XML"""
        self.is_folder = False
        is_folder = self.parser.get_key_bool_value(self.parser.node, "Folder")
        if is_folder == "true":
            self.is_folder = True

    def set_is_smart(self):
        """Sets the value of self.is_smart by finding whether the "Smart Info" key exists in the XML"""
        self.is_smart = self.parser.get_key(self.parser.node, "Smart Info") is not None

    def set_items(self):
        """Sets the list of items in the Playlist"""
        if DEBUG:
            print("Setting items for playlist \"" + self.name + "\"")
        self.items = self.parser.get_tracks_info()
        if DEBUG:
            print("Finished setting info for \"" + self.name + "\"")

    def get_total_length(self):
        """Returns the total length in seconds of this Playlist"""
        total = 0
        for item in self.items:
            total += item['length']

        return total

    def set_quick(self):
        """Calls the quick set functions above"""
        self.set_name()
        self.set_persistent_ID()
        self.set_parent_ID()
        self.set_is_folder()
        self.set_is_smart()

class iTunes_Library():
    """Information about an iTunes XML Library"""

    def __init__(self, xml_file):
        self.xml_file = xml_file
        self.parser = iTunes_Library_Parser(self.xml_file)

    def get_playlists(self):
        """Sets the non time consuming information for each playlist (everything except items)"""

        # create array to contain Playlist_Parser objects
        self.playlists = []
        playlists_key = self.parser.get_key(self.parser.document, "Playlists")
        playlists_node = playlists_key.nextSibling.nextSibling

        # create a Playlist object for each playlist
        for node in playlists_node.childNodes:
            if not node.nodeType == node.TEXT_NODE:
                playlist = Playlist(node, self.xml_file, self.parser.document)
                playlist.set_quick()
                self.playlists.append(playlist)

    def get_items(self, playlists, export_all):
        """Creates Playlist object for each playlist found and adds them to a list"""

        # get the playlists if necessary
        if not hasattr(self, "playlists"):
            self.get_playlists()

        force_select = False
        
        # ask the user to select the playlists to export if none are specified
        if len(playlists) == 0 and export_all == False:
            playlists = self.select_playlists()
            force_select = True

        self.export = []
        # set the items for the playlists specified to export
        for playlist in self.playlists:
            if export_all or playlist.name in playlists:
                if DEBUG:
                    print("Adding playlist " + playlist.name + " to self.export")
                playlist.set_items()
                self.export.append(playlist)

        # check to see if any playlists were excluded from self.export
        if len(playlists) > 0 and not force_select:

            # make list of names of playlists to be exported
            names_list = []
            for playlist in self.export:
                names_list.append(playlist.name)
            check_for_excluded(playlists, names_list)

    def get_num_playlist_ancestors(self, Playlist):
        """Determines the Playlist's place in the directory structure"""

        num_ancestors = 0
        current_ancestor = Playlist

        # while the current ancestor has a parent
        while current_ancestor.parent_ID is not None:

            # find the current ancestor's parent by looping through the array
            check_num = 0
            check = self.playlists[check_num]

            while not check.persistent_ID == current_ancestor.parent_ID:
                check_num += 1
                check = self.playlists[check_num]

            # set the current ancestor's parent as the new current ancestor
            current_ancestor = check
            num_ancestors += 1

        return num_ancestors

    def select_playlists(self):
        """Prints the playlists in the library indented by their folder levels"""

        # get the playlists
        if not hasattr(self, "playlists"):
            self.get_playlists()

        print("You have not specified any playlists to export! " +
              "The playlists available will now be printed, " +
              "please enter y to export the playlist or n to skip it.")

        chosen = []
        satisfied = False
        tab = " " * TAB_SIZE
        
        # loop through the playlists and print them appropriately
        while not satisfied:
            for playlist in self.playlists:

                # determine its indentation level
                indents = self.get_num_playlist_ancestors(playlist)
                tab_string  = tab * indents

                # determine the type of Playlist
                type_string = ""
                if playlist.is_smart:
                    type_string += "Smart "
                if playlist.is_folder:
                    type_string += "Folder"
                else:
                    type_string += "Playlist"


                input_start = tab_string + playlist.name
                input_end = " <" + type_string + "> [y/n]? "
                filler_string = " " * (TABLE_WIDTH - len(input_start) - len(input_end))

                # print the Playlist
                export = input(input_start + filler_string + input_end)

                # determine whether to export the playlist
                if export == "y":
                    chosen.append(playlist)

            # run the playlist chooser until the user is satisfied with their selection
            chosen_string = (''.join(str(choice.name) + ", " for choice in chosen)).rstrip(", ")
            report = input('Playlists to be exported are: ' + chosen_string + '\n' +
                           'To continue, type "y", to choose a new ' +
                           'set of playlists, type "n" ')
            if not report == "n":
                satisfied = True

        return chosen
                

class Playlist_Writer():
    """Writes playlists to disk"""

    def __init__(self, playlist, root, extension):

        self.playlist = playlist
        self.root = root
        self.extension = extension
        self.location = normalize_path(os.path.join(root, self.playlist.name + extension))

    def playlist_exists(self):
        """Tests whether the file to write to already exists"""

        # try to open file to read it
        try:
            file = open(self.location, 'r')

        # if it fails, then the file doesn't exist
        except IOError:
            return False

        file.close()
        return True

    def write_file(self):
        raise NotImplementedError("Subclass must implement abstract method")

    def change_location(self):
        """Determines location based on whether the user wishes to overwrite existing playlist"""

        # variables for the loop
        first = True
        counter = 2

        name = self.playlist.name + self.extension
        # change the name of the playlist while the location is occupied
        while self.playlist_exists():
            if first == True:
                overwrite = input("File " + name + " exists. Overwrite? [y/n] ")
                first = False

                # if the user chooses not to overwrite, exit the loop
                if overwrite == "y":
                    print("Will overwrite " + name)
                    break
                else:
                    print("Creating new name for \"" + name + "\"")

            # give the playlist a new name
            new_name = self.playlist.name + " (" + str(counter) + ")" + self.extension
            
            self.location = normalize_path(os.path.join(self.root, new_name))
            counter += 1

            print("new name for " + self.playlist.name + " is " + new_name)


class WPL_Writer(Playlist_Writer):
    """Writes WPL playlists to disk"""

    def __init__(self, playlist, root):
        super().__init__(playlist, root, ".wpl")

    def write_file(self):
        """Writes the playlist file"""

        if DEBUG:
            print("Writing file for " + self.playlist.name)
        
        # open the file as utf8
        file = codecs.open(self.location, 'w', "utf-8")

        # HEADER
        # write initial data
        file.write(r'<?wpl version = "1.0"?>')
        file.write("\n" + r"<smil>")
        file.write("\n" + "\t" + r"<head>")

        # write meta data
        file.write("\n" + "\t" + "\t" +
                   r"""<meta name = "Generator" content = "Kar's iTunes Export Python Script"/>""")
        file.write("\n" + "\t" + "\t" + r'<meta name = "TotalDuration" content = ' + "\""
                   + str(self.playlist.get_total_length()) + r'"/>')
        file.write("\n" + "\t" + "\t" + r'<meta name = "ItemCount" content = ' + "\""
                   + str(len(self.playlist.items)) + r'"/>')
        file.write("\n" + "\t" + "\t" + r"<author>" + AUTHOR + r"</author>")
        file.write("\n" + "\t" + "\t" + r"<title>" + self.playlist.name + r"</title>")
        file.write("\n" + "\t" + r"</head>")

        # begin writing body
        file.write("\n" + "\t" + r"<body>")
        file.write("\n" + "\t" + "\t" + r"<seq>")

        # BODY
        for item in self.playlist.items:
            file.write("\n" + "\t" + "\t" + "\t")
            clean_loc = self.clean_string(item['location'])
            file.write(r'<media src = "' + clean_loc + "\"" + r'/>')

        # FOOTER
        # finish writing the file
        file.write("\n" + "\t" + "\t" + r"</seq>")
        file.write("\n" + "\t" + r"</body>")
        file.write("\n" + r"</smil>")

        # close the file
        file.close()

    def clean_string(self, location):
        """Cleans the location of characters that will break the file"""
        return location.replace("&", "&amp;")


class M3U8_Writer(Playlist_Writer):
    """Writes m3u8 playlist files to disk"""

    def __init__(self, playlist, root):
        super().__init__(playlist, root, ".m3u8")

    def write_file(self):
        """Writes the playlist file"""

        if DEBUG:
            print("Writing file for " + self.playlist.name)

        sep = os.linesep

        # open the file as utf8
        file = codecs.open(self.location, 'w', "utf-8")

        # HEADER
        file.write(r'#EXTM3U')

        # BODY
        for item in self.playlist.items:
            file.write(sep + r"#EXTINF:" + str(int(round(item['length'], 0))) + "," +
                       item['name'] + " - " + item['artist'])
            file.write(sep + item['location'])

        # close the file
        file.close()           
        
        

##################################################################
## FUNCTIONS
##################################################################

def get_settings_location():
    """Get the playlist info text file from the current directory"""

    # set up the path
    path_name = os.path.dirname(sys.argv[0])
    settings_location = os.path.abspath(path_name)

    # normalize and return the entire path
    return normalize_path(os.path.join(settings_location, SETTINGS_NAME + ".txt"))

def get_settings_lines():
    """Returns a list of the lines in the settings file"""

    settings_location = get_settings_location();

    # open the file if it exists, create the file if it doesn't
    try:
        settings_file = open(settings_location, 'r')
    except IOError:
        settings_file = open(settings_location, 'w')
        settings_file.close()
        settings_file = open(settings_location, 'r')
    
    settings_lines = settings_file.readlines()

    # close the file and return the lines
    settings_file.close()
    return settings_lines


def confirm_name(info_lines, line_num, filetypes, title):
    """GUI asks user to choose a file/directory if the existing cannot be found"""

    # set initial variables, if filetypes is blank, then a directory is wanted
    path = info_lines[line_num - 1].rstrip('\r\n')
    directory = filetypes is None

    # if the path does not exist, prompt for a new one
    if not os.path.exists(path):
        if DEBUG:
            print("path " + str(path) + " does not exist")
        Tk().withdraw()
        if directory:
            path = askdirectory(title = title)
        else:
            path = askopenfilename(filetypes = filetypes, title = title)

        # throw SystemExit exception if the user does not choose a valid path
        if not os.path.exists(path):
            sys.exit() 

        # save the new path to the array if the user chooses a valid path
        else:
            if DEBUG:
                print(str(info_lines[line_num - 1]).rstrip('\r\n') +
                      " will be changed to " + str(path))
            info_lines[line_num - 1] = path + "\n"
    elif DEBUG:
        print(str(path) + " exists")

    return path

def normalize_path(path):
    """Normalize the path by replacing all the slashes with the default system slash"""

    # replace forward slashes in Windows and backslashes otherwise
    if system() == "Windows":
        return path.replace("/", "\\")
    else:
        return path.replace("\\", "/")
        

def save(lines):
    """Save the changes made to the settings file by rewriting its contents"""
    
    file = open(get_settings_location(), 'w')
    file.writelines(lines)
    file.close()

def create_writers(playlists, extension, export_location):
    """Creates and returns a list of writers corresponding to the extension and playlists"""

    writers = []

    # if the extension is WPL, make a WPL_Writer for all the playlists given
    if extension.lower() == "wpl":
        for playlist in playlists:
            writers.append(WPL_Writer(playlist, export_location))

    # if the extension is M3U8, make an M3U8_Writer for all the playlists given
    if extension.lower() == "m3u8":
        for playlist in playlists:
            writers.append(M3U8_Writer(playlist, export_location))

    return writers

def determine_writers(playlists, args, export_location):
    """Returns a list of writers corresponding to command line arguments or constants"""

    writers = []

    # for every extension given, create a corresponding Playlist_Writer
    for extension in args.extension:
        
        if extension.lower() == "wpl":
            for playlist in playlists:
                writers.append(WPL_Writer(playlist, export_location))

        if extension.lower() == "m3u8":
            for playlist in playlists:
                writers.append(M3U8_Writer(playlist, export_location))

    return writers

def check_for_excluded(list1, list2):
    """Check to see if every item in list1 is in list2"""
    
    for item in list1:
        if not item in list2:
            sys.stderr.write("Item " + item + " not found!\n")


def command_line_args():
    """Set up command line arguments"""
    
    # create the argument parser
    parser = argparse.ArgumentParser(description = "Export iTunes playlists")

    # set up the available arguments
    parser.add_argument('-a', '--all', action = 'store_true', help = "export all playlists")
    parser.add_argument('-e', '--extension', nargs = '*', default = [DEFAULT_FORMAT], help =
                        "specify the extension of the playlist in the form 'wpl' or 'm3u8'")
    parser.add_argument('-p', '--playlists', nargs = '*', help = "specify the playlists to export")
    parser.add_argument('-f', '--file', action = 'store_true',
                        help = "export playlists specified in a text file (use the settings" +
                        "file to specify the location of the text file)")

    # parse and return the arguments
    args = parser.parse_args()
    return args

def settings_file(args):
    """Deal with settings file"""
    
    lines = get_settings_lines()
    
    # test to see if the paths in the file exist, prompt for new ones if they don't
    try:
        library_location = confirm_name(lines, 1, [('xml files', '.xml')],
                                        "Choose iTunes library xml file")
        export_location = confirm_name(lines, 2, None,
                                       "Choose the directory for the files to be exported")
        playlists_location = None
        if args.file:
            playlists_location = confirm_name(lines, 3, [('Text files', '.txt')],
                                              "Choose the location of the text file " +
                                              "containing the playlists")
    
    # if a user does not choose a directory, catch the SystemExit exception, save and exit
    except SystemExit:
        print("Correct file/folder was not chosen, script will now save and exit")
        save(lines)
    else:
        save(lines)

    return library_location, export_location, playlists_location

def write_playlists(args, library_location, export_location, playlists_location):
    """Create the iTunes Library object and write the playlists"""

    playlist_names = args.playlists
    if playlist_names is None:
        playlist_names = []
    
    # create a list of playlists if they were given
    if playlists_location is not None:

        # set up file to be read
        playlist_names = []
        playlists_file = open(playlists_location, 'r')
        playlist_line = playlists_file.readline()

        # read all the lines in the file
        while not playlist_line == '':
            playlist_names.append(playlist_line.rstrip('\r\n'))
            playlist_line = playlists_file.readline()

        # close the file
        playlists_file.close()

    # create the library and get the items to export
    library = iTunes_Library(library_location)
    library.get_items(playlist_names, args.all)
    print("Items to export are " + str(library.export))

    # create writers for the items and write them to disk
    writers = determine_writers(library.export, args, export_location)
    for writer in writers:
        writer.change_location()
        writer.write_file()

##################################################################
## BODY
##################################################################

if __name__ == "__main__":
    args = command_line_args()
    library_location, export_location, playlists_location = settings_file(args)
    write_playlists(args, library_location, export_location, playlists_location)
    print("Finished writing playlists, will now exit!")
    

    


