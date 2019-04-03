from os import makedirs, remove
from os.path import abspath, dirname, exists
try:
    import bpy
except ModuleNotFoundError:
    # For building the doc
    pass

from xiuminglib import config
logger, thisfile = config.create_logger(abspath(__file__))


def save_blend(outpath, delete_overwritten=False):
    """Saves current scene to a .blend file.

    Args:
        outpath (str): Path to save scene to, e.g., ``'~/foo.blend'``.
        delete_overwritten (bool, optional): Whether to delete or keep as .blend1 the same-name file.
    """
    logger_name = thisfile + '->save_blend()'

    outdir = dirname(outpath)
    if not exists(outdir):
        makedirs(outdir)
    elif exists(outpath) and delete_overwritten:
        remove(outpath)

    try:
        bpy.ops.file.autopack_toggle()
    except RuntimeError:
        logger.name = logger_name
        logger.error("Failed to pack some files")

    bpy.ops.wm.save_as_mainfile(filepath=outpath)

    logger.name = logger_name
    logger.info("Saved to %s", outpath)
