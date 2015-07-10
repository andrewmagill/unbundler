import os, sys, mmap, re, struct
from collections import namedtuple

def bundle_name(row, col):
    """returns the name of the bundle that will hold the image,
    if it exists, given the row and column of that image
    """
    # round down to nearest 128
    row = int(row / 128)
    row = row * 128

    col = int(col / 128)
    col = col * 128

    row = "%04x" % row
    col = "%04x" % col

    name = "R{}C{}".format(row, col)
    return name

def index_position(row, col):
    """given a row and column, returns the position in the index
    file where you can find the position of the actual image
    in the bundle file
    """
    row = row % 128
    col = col % 128

    base_pos = col * 128 * 5 + 16
    offset = row * 5

    position = base_pos + offset
    return position

def sum_bytes(chunk):
    """little endian
    """
    if len(chunk) > 5:
        raise Exception("Invalid byte chunk")

    if type(chunk[0]) is int:
        value  = chunk[0] * 1
        value += chunk[1] * 256
        value += chunk[2] * 65536
        value += chunk[3] * 16777216
        value += chunk[4] * 4294967296
    else:
        value  = int(chunk[0].encode('hex'), 16) * 1
        value += int(chunk[1].encode('hex'), 16) * 256
        value += int(chunk[2].encode('hex'), 16) * 65536
        value += int(chunk[3].encode('hex'), 16) * 16777216
        value += int(chunk[4].encode('hex'), 16) * 4294967296

    return value

TileInfo = namedtuple("TileInfo",["path","row","column"])
tile_pos_dict = {}

def tile_position(path, row, column):
    """reads from the index file and returns the position of the
    image in the bundle file, given the path of the index file
    and the row and column fo the image
    """
    tile_info = TileInfo(path=path, row=row, column=column)
    if tile_info in tile_pos_dict.keys():
        #print("returning positiong from dictionary")
        return tile_pos_dict[tile_info]

    position = index_position(row, column)
    path += ".bundlx"

    file = open(path, 'r+b')

    length = position % mmap.PAGESIZE + 5
    start = int(position/mmap.PAGESIZE) * mmap.PAGESIZE
    file_size = os.fstat(file.fileno()).st_size
    if length > file_size - start:
        length = file_size - start

    mm = mmap.mmap(file.fileno(), length, offset=start)

    m = position - start
    n = m + 5

    tile_pos = sum_bytes(mm[m:n])

    mm.close()
    file.close()

    tile_pos_dict[tile_info] = tile_pos
    return tile_pos

def tile_image(path, row, column):
    """returns the binary array of the image from the bundle file,
    given the path of the bundle file, and the row and column
    of the image
    """
    position = tile_position(path, row, column)

    path += ".bundle"
    file = open(path, 'r+b')

    # this is a hack that could break things,
    # but hopefully saves a lot of memory
    length = 8 * mmap.PAGESIZE
    start = int(position/mmap.PAGESIZE) * mmap.PAGESIZE
    file_size = os.fstat(file.fileno()).st_size
    if length > file_size - start:
        length = file_size - start

    mm = mmap.mmap(file.fileno(), length, offset=start)

    # read the size of the embedded image
    m = position-start
    n = m + 4

    size = struct.unpack('i',mm[m:n])[0]

    # read the size the image itself
    m = n
    n = m + size

    image = mm[m:n]

    print("path: {}, pos: {}, size: {}, row: {}, col: {}"\
                    .format(path, position, size, row, column))

    mm.close()
    file.close()

    return image

def get_map_tile(level, row, column):
    """returns the binary array of the image, if it exists, given the
    level, row and column
    """
    level = "L%02d" % int(level)
    row   = int(row)
    col   = int(column)

    path  = os.path.join("files/", level, bundle_name(row, col))
    image = None

    try:
        image = tile_image(path, row, col)
    except (IOError, OSError) as e:
        print("{}: {}".format(type(e), e.strerror))
    except Exception as e:
        print("{}: {}".format(type(e), e.args))

    return image

def main(args):
    try:
        level = int(args[1])
        row = int(args[2])
        col = int(args[3])
    except:
        print ( "please provide integer arguments for the "
                "level, row, and column of the image you seek" )
        sys.exit()

    image = get_map_tile(level, row, col)

    if image:
        name = '{}R{}C{}.png'.format(level, row, col)
        print("DEBUG: writing to file {}".format(name))
        file = open(name,'w+b')
        file.write(image)
        file.close()
    else:
        print("image not found")

if __name__== "__main__":
    main(sys.argv)
