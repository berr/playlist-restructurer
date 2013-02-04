import sys
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
import mutagen
import os.path
import optparse
import shutil

usage = 'Usage: %prog <options> source_dir dest_dir'

parser = optparse.OptionParser(usage)


parser.add_option('-v', '--verbose', help='Show extra information', dest='verbose', default=False, action='store_true')
parser.add_option('-p', '--pretend', help="Don't execute any restructuring action", dest='pretend', default=False, action='store_true')
parser.add_option('-m', '--move', help="Move files instead of copying. Attention: Destructive", dest='use_move', default=False, action='store_true')

(opts, args) = parser.parse_args()


if len(args) != 2:
    print 'Missing source and destiny folders'
    print ''
    parser.print_help()
    sys.exit(1)

USE_MOVE = opts.use_move
VERBOSE = opts.verbose
PRETEND = opts.pretend


source_dir = args[0]
dest_dir = args[1]


################################################################################
#                                 Info objects                                 #
################################################################################
class NameBasedObject(object):

    def __init__(self, name):
        self.name = name

    def __hash__(self):
        return self.name.__hash__()

    def __eq__(self, o):
        if isinstance(o, NameBasedObject):            
            return self.name == o.name
        return o == self.name
        
    def __repr__(self):
        return self.name

    def __str__(self):
        return name


class Artist(NameBasedObject):

    def __init__(self, name):
        NameBasedObject.__init__(self, name)


class Album(NameBasedObject):

    def __init__(self, name, year):
        NameBasedObject.__init__(self, name)
        self.year = year


class Song(NameBasedObject):

    def __init__(self, name, track):
        NameBasedObject.__init__(self, name)
        self.track = track



################################################################################
#                                 Error Types                                  #
################################################################################
class NoSuchAttribute(RuntimeError):

    def __init__(self, attribute):
        RuntimeError.__init__(self)
        self.attribute = attribute

class InvalidAttribute(RuntimeError):
    
    def __init__(self, attribute):
        RuntimeError.__init__(self)
        self.attribute = attribute

class EmptyAttribute(RuntimeError):
    
    def __init__(self, attribute):
        RuntimeError.__init__(self)
        self.attribute = attribute


################################################################################
#                          Helpers to obtain tag values                        #
################################################################################
def get_attribute(info, name, caption):
    try:
        r = info[name][0]
    except KeyError:
        raise NoSuchAttribute(caption)

    if r.strip() == '':
        raise EmptyAttribute(caption)

    return r

def get_album(info):
    return get_attribute(info, 'album', 'Album')

def get_artist(info):
    return get_attribute(info, 'artist', 'Artist')

def get_date(info):
    return get_attribute(info, 'date', 'Year')

def get_title(info):
    return get_attribute(info, 'title', 'Title')

def get_track_number(info):
    
    try:
        track_number = info['tracknumber'][0]
    except KeyError:
        raise NoSuchAttribute('Track Number')

    if track_number.strip() == '':
        raise EmptyAttribute('Track Number')

    try:
        return int(track_number)
    except ValueError:
        pass

    # The track number is on the form 1/10
    actual_track_number, total_tracks = track_number.split('/')
    try:
        return int(actual_track_number)
    except ValueError:
        # Ok, don't know what to do
        raise InvalidAttribute('Track Number')



################################################################################
#                               Populate library                               #
################################################################################
def get_objects_from_info(info):
    artist = Artist(get_artist(info))
    album = Album(get_album(info), get_date(info))
    song = Song(get_title(info), get_track_number(info))


    return (artist, album, song)

library = {}
def convert_dir(arg, dir_name, files):
    for f in (x for x in files if x.lower().endswith('mp3')):
        file_path = os.path.join(dir_name, f)

        try:
            info = MP3(file_path, ID3=EasyID3)
        except mutagen.mp3.HeaderNotFoundError:
            print "File %s doesn't have header" % file_path
            continue
            
        try:
            artist, album, song = get_objects_from_info(info)
        except NoSuchAttribute, e:
            print '''File %s: attribute "%s" is not present''' % (file_path, e.attribute)
            continue
        except EmptyAttribute, e:
            print '''File %s: attribute "%s" is empty''' % (file_path, e.attribute)
            continue
        except InvalidAttribute, e:
            print '''File %s: attribute "%s" has unknown format''' % (file_path, e.attribute)
            continue

        if artist not in library:
            library[artist] = {}
        
        albums_by_artist = library[artist]

        if album not in albums_by_artist:
            albums_by_artist[album] = []

        songs_by_album = albums_by_artist[album]
        
        songs_by_album.append((file_path, song))


os.path.walk(source_dir, convert_dir, arg=None)



################################################################################
#                                   Commands                                   #
################################################################################

def mkdir(dir):
    if VERBOSE:
        print 'mkdir', dir
    if not PRETEND:
        os.mkdir(dir)

def mv(src, dest):
    if VERBOSE:    
        print 'mv', src, dest
    if not PRETEND:
        shutil.move(src, dest)

def cp(src, dest):
    if VERBOSE:
        print 'cp', src, dest
    if not PRETEND:
        shutil.copy(src, dest)



################################################################################
#                               File/Folder Name                               #
################################################################################

def get_artist_folder_name(artist):
    return artist.name.replace('/','-')

def get_album_folder_name(artist, album):
    return ' - '.join([str(album.year), album.name.replace('/','-')])

def get_song_name(artist, album, song):
    return ' - '.join(['%02d' % song.track, song.name.replace('/','-')])


################################################################################
#                                  Conversion                                  #
################################################################################
for artist in library:
    artist_dir = os.path.join(dest_dir, get_artist_folder_name(artist))
    mkdir(artist_dir)
    for album in library[artist]:
        album_dir = os.path.join(artist_dir, get_album_folder_name(artist, album))
        mkdir(album_dir)
        for old_path, song in library[artist][album]:
            song_name = get_song_name(artist, album, song) + '.mp3'
            if USE_MOVE:
                mv(old_path, os.path.join(album_dir, song_name))
            else:
                cp(old_path, os.path.join(album_dir, song_name))

            


