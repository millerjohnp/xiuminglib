from os import makedirs
from os.path import abspath, dirname, exists, join, basename
import numpy as np
import cv2

from xiuminglib import config
logger, thisfile = config.create_logger(abspath(__file__))


class EXR():
    """Reads EXR files.

    EXR files can be generic or physically meaningful, such as depth, normal, etc.
    When data loaded are physically meaningful, these methods assume the EXR files
    are produced by :mod:`xiuminglib.blender.render` and hence follow certain formats.

    Attributes:
        exr_path (str): Path to the EXR file.
    """
    def __init__(self, exr_path):
        self.exr_f = exr_path
        self.data = self.load()

    def load(self):
        """Loads an EXR as a dictionary of NumPy arrays.

        Requires writing a ``.npz`` to ``/tmp/`` and then loading it, because
        the conversion process has to be done in Python 2.x as a subprocess call,
        unfortuantely (in-memory loading with OpenCV handles <=3 channels).

        Returns:
            data (dict): Loaded EXR data.
        """
        from time import time
        from subprocess import Popen, PIPE
        npz_f = '/tmp/%s_t%s.npz' % \
            (basename(self.exr_f).replace('.exr', ''), time())
        # Convert to .npz
        # cv2.imread() can't load more than three channels from .exr even with IMREAD_UNCHANGED
        # Has to go through IO. Maybe there's a better way?
        cwd = join(dirname(abspath(__file__)), '..', '..', 'cli')
        bash_cmd = 'python2 exr2npz.py %s %s' % (self.exr_f, npz_f)
        process = Popen(bash_cmd.split(), stdout=PIPE, cwd=cwd)
        out, err = process.communicate()
        print(err)
        # Load this .npz
        data = np.load(npz_f)
        return data

    def extract_depth(self, alpha_exr, outpath, vis_raw=False):
        """Combines an aliased, raw depth map and its alpha map into a ``.npy`` image.

        Output has black background, with bright values for closeness to the camera.
        If the alpha map is anti-aliased, the result depth map will be nicely anti-aliased.

        Args:
            alpha_exr (str): Path to the EXR file of the anti-aliased alpha map.
            outpath (str): Path to the result ``.npy`` file.
            vis_raw (bool, optional): Whether to visualize the raw values as an image.
                Defaults to False.
        """
        logger_name = thisfile + '->extract_depth()'
        dtype = 'uint8'
        dtype_max = np.iinfo(dtype).max
        # Load alpha
        arr = cv2.imread(alpha_exr, cv2.IMREAD_UNCHANGED)
        assert (arr[:, :, 0] == arr[:, :, 1]).all() and (arr[:, :, 1] == arr[:, :, 2]).all(), \
            "A valid alpha map must have all three channels the same"
        alpha = arr[:, :, 0]
        # Load depth
        arr = cv2.imread(self.exr_f, cv2.IMREAD_UNCHANGED)
        assert (arr[..., 0] == arr[..., 1]).all() and (arr[..., 1] == arr[..., 2]).all(), \
            "A valid depth map must have all three channels the same"
        depth = arr[..., 0] # these raw values are aliased, so only one crazy big value
        if not outpath.endswith('.npy'):
            outpath += '.npy'
        np.save(outpath, np.dstack((arr, alpha)))
        if vis_raw:
            is_fg = depth < depth.max()
            max_val = depth[is_fg].max()
            depth[depth > max_val] = max_val # cap background depth at the object maximum depth
            min_val = depth.min()
            im = dtype_max * (max_val - depth) / (max_val - min_val) # [0, dtype_max]
            # Anti-aliasing
            bg = np.zeros(im.shape)
            im = np.multiply(alpha, im) + np.multiply(1 - alpha, bg)
            cv2.imwrite(outpath[:-4] + '.png', im.astype(dtype))
        logger.name = logger_name
        logger.info("Depth image extractd to %s", outpath)

    def extract_normal(self, outpath, vis=False):
        """Converts an RGBA EXR normal map to a ``.npy`` normal map.

        The background is black, complying with industry standards (e.g., Adobe AE).

        Args:
            outpath (str): Path to the result ``.npy`` file.
            vis (bool, optional): Whether to visualize the normal vectors as an image.
                Defaults to False.
        """
        logger_name = thisfile + '->extract_normal()'
        dtype = 'uint8'
        dtype_max = np.iinfo(dtype).max
        # Load RGBA .exr
        data = self.data
        arr = np.dstack((data['R'], data['G'], data['B']))
        alpha = data['A']
        if not outpath.endswith('.npy'):
            outpath += '.npy'
        np.save(outpath, np.dstack((arr, alpha)))
        if vis:
            # [-1, 1]
            im = (1 - (arr / 2 + 0.5)) * dtype_max
            # [0, dtype_max]
            bg = np.zeros(im.shape)
            alpha = np.dstack((alpha, alpha, alpha))
            im = np.multiply(alpha, im) + np.multiply(1 - alpha, bg)
            cv2.imwrite(outpath[:-4] + '.png', im.astype(dtype)[..., ::-1])
        logger.name = logger_name
        logger.info("Normal image extractd to %s", outpath)

    def extract_intrinsic_images_from_lighting_passes(self, outdir, vis=False):
        """Extract intrinsic images from an EXR of lighting passes into multiple ``.npy`` files.

        Args:
            outdir (str): Directory to save the result ``.npy`` files to.
            vis (bool, optional): Whether to visualize the values as images.
                Defaults to False.
        """
        from xiuminglib import visualization as xv
        logger_name = thisfile + '->extract_intrinsic_images_from_lighting_passes()'
        if not exists(outdir):
            makedirs(outdir)
        data = self.data

        def collapse_passes(components):
            ch_arrays = []
            for ch in ['R', 'G', 'B']:
                comp_arrs = []
                for comp in components:
                    comp_arrs.append(data[comp + '.' + ch])
                ch_array = np.sum(comp_arrs, axis=0) # sum components
                ch_arrays.append(ch_array)
            # Handle alpha channel
            first_alpha = data[components[0] + '.A']
            for ci in range(1, len(components)):
                assert (first_alpha == data[components[ci] + '.A']).all(), \
                    "Alpha channels of all passes must be the same"
            ch_arrays.append(first_alpha)
            return np.dstack(ch_arrays)

        # Albedo
        albedo = collapse_passes(['diffuse_color', 'glossy_color'])
        np.save(join(outdir, 'albedo.npy'), albedo)
        if vis:
            xv.matrix_as_image(albedo, outpath=join(outdir, 'albedo.png'))
        # Shading
        shading = collapse_passes(['diffuse_indirect', 'diffuse_direct'])
        np.save(join(outdir, 'shading.npy'), shading)
        if vis:
            xv.matrix_as_image(shading, join(outdir, 'shading.png'))
        # Specularity
        specularity = collapse_passes(['glossy_indirect', 'glossy_direct'])
        np.save(join(outdir, 'specularity.npy'), specularity)
        if vis:
            xv.matrix_as_image(specularity, join(outdir, 'specularity.png'))
        # Reconstruction vs. ...
        recon = np.multiply(albedo, shading) + specularity
        recon[:, :, 3] = albedo[:, :, 3] # can't add up alpha channels
        np.save(join(outdir, 'recon.npy'), recon)
        if vis:
            xv.matrix_as_image(recon, join(outdir, 'recon.png'))
        # ... composite from Blender, just for sanity check
        composite = collapse_passes(['composite'])
        np.save(join(outdir, 'composite.npy'), composite)
        if vis:
            xv.matrix_as_image(composite, join(outdir, 'composite.png'))
        logger.name = logger_name
        logger.info("Intrinsic images extracted to %s", outdir)


def main():
    """Unit tests that can also serve as example usage."""
    from os import environ
    tmp_dir = environ['TMP_DIR']
    exr_f = join(tmp_dir, 'test.exr')
    exr = EXR(exr_f)


if __name__ == '__main__':
    main()
