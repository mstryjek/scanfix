import os
import time
import glob
import cv2
from PIL import Image

import numpy as np
from typing import Tuple, List




IMAGE_FORMATS = ['jpg', 'png', 'bmp', 'tiff']


class ImageHandler():
    """
    OS I/O class for images and pdfs.
    """
    def __init__(self, cfg) -> None:
        self.CFG = cfg
        self.flag = cv2.IMREAD_GRAYSCALE if self.CFG.READ_GRAYSCALE else cv2.IMREAD_COLOR
        self.cnt = 0
        self.read_from_device()
        self.sort_names_by_indices()
        self.discard_old()
        self.load()


    def __iter__(self):
        self.cnt = 0
        return self


    def __next__(self) -> Tuple[str, np.ndarray]:
        """Return the next filename and image."""
        if self.cnt == len(self.files):
            raise StopIteration

        filename = str(self.files[self.cnt])
        img = self.images[self.cnt]
        self.cnt += 1

        return (os.path.split(filename)[-1], img)


    def __len__(self) -> int:
        """Magic method overload, may be useful in the future."""
        return len(self.files)


    def max(self) -> int:
        """Method for convenience."""
        if len(self.files) == 0:
            return -1
        return int(max(self.indices))


    def read_from_device(self) -> None:
        """
        Load images from device.
        """
        filenames_local = self.CFG.IMAGE_PREFIX + '*.' + self.CFG.IMAGE_EXTENSION
        path = os.path.join(self.CFG.DEVICE_PATH, filenames_local)
        self.files = np.array(glob.glob(path))


    def load(self) -> None:
        """Load images from device after they have been filtered."""
        self.images = [cv2.imread(f, self.flag) for f in self.files]


    def sort_names_by_indices(self) -> None:
        """Sort files by their order of creation."""
        self.indices = np.array(list(map(self.image_name_to_index, self.files)))
        order = np.argsort(self.indices)

        self.indices = self.indices[order]
        self.files = self.files[order]


    def image_name_to_index(self, name: str) -> int:
        """Convert automatically generated image name to image index."""
        ## Convert image path to local filename
        name = os.path.split(name)[-1]

        ## Remove prefix automatically generated by device
        if name.startswith(self.CFG.IMAGE_PREFIX):
            name = name[len(self.CFG.IMAGE_PREFIX):]

        ## Remove image extenstion(s)
        name = name.split('.')[0]

        ## Remove heading zeros (image filenames have a fixed number of digits)
        idx = name.lstrip('0')
        return int(idx)


    def discard_old(self) -> None:
        """Discard images previously processed."""
        files_not_used = np.where(self.indices > self.CFG.LAST_IMAGE_IDX)
        self.files = self.files[files_not_used]
        self.indices = self.indices[files_not_used]


    def resize_to_A4(self, img: np.ndarray) -> np.ndarray:
        """
        Resize image to A4 page size with given DPI (see config).
        """
        ## Standardized A4 sizes in px @ 300DPI
        h = int(3508 * (300/self.CFG.SAVE_DPI))
        w = int(2480 * (300/self.CFG.SAVE_DPI))
        return cv2.resize(img, (w, h))


    def get_pdf_filename(self) -> str:
        """Get unique pdf filename."""
        filename_no_ext = self.CFG.SAVE_PREFIX + '_' + time.strftime('%d_%m_%y-%H_%M') + '.pdf'
        return os.path.join(self.CFG.SAVE_PATH, filename_no_ext)


    def save(self, images: List[np.ndarray]) -> None:
        """Save images as separate images or a .pdf file."""
        if len(self.files) == 0:
            return

        ## Create output directory if it does not exist
        if not os.path.exists(self.CFG.SAVE_PATH):
            os.mkdir(self.CFG.SAVE_PATH)

        ## Convert to RGB
        if len(images[0].shape) == 3:
            images = [cv2.cvtColor(img, cv2.COLOR_BGR2RGB) for img in images]

        ## Resize to A4 size
        images = [self.resize_to_A4(img) for img in images]

        ## Save images as images
        if self.CFG.SAVE_FORMAT.lower() in IMAGE_FORMATS:
            for i in range(len(images)):
                filename = os.path.join(self.CFG.SAVE_PATH, os.path.split(self.files[i])[-1])
                cv2.imwrite(filename, images[i])

        ## Save images as pdf
        else:
            ## Convert to Pillow format
            pil_imgs = [Image.fromarray(img) for img in images]
            root = pil_imgs.pop(0)
            filename = self.get_pdf_filename()
            root.save(filename, 'PDF', save_all=True, append_images=pil_imgs)


