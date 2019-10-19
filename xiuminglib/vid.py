from os.path import abspath, join

from .config import create_logger
logger, thisfile = create_logger(abspath(__file__))

from . import const
from .imprt import preset_import
cv2 = preset_import('cv2')


def images2video(imgs, fps=24, outpath=None):
    """Writes a list of images into a grayscale or color video.

    Args:
        imgs (list(numpy.ndarray)): Each image should be of type ``uint8`` or
            ``uint16`` and of shape H-by-W (grayscale) or H-by-W-by-3 (color).
        fps (int, optional): Frame rate.
        outpath (str, optional): Where to write the video to (a .avi file).
            ``None`` means ``os.path.join(const.Dir.tmp, 'images2video.avi')``.

    Writes
        - A video of the images.
    """
    from cv2 import VideoWriter, VideoWriter_fourcc

    logger_name = thisfile + '->images2video()'

    if outpath is None:
        outpath = join(const.Dir.tmp, 'images2video.avi')

    h, w = imgs[0].shape[:2]

    fourcc = VideoWriter_fourcc(*'MP42')
    vw = VideoWriter(outpath, fourcc, fps, (w, h))

    for frame in imgs:
        assert frame.shape[:2] == (h, w), "All frames must have the same shape"
        vw.write(frame)

    vw.release()

    logger.name = logger_name
    logger.info("Images written as a video to:\n%s", outpath)