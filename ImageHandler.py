from __future__ import annotations
from typing import Optional
import io
import os
import shutil
import glob
import rawpy
from PIL import Image


class ImageObject:
    def __init__(self, nef_file: str = None, jpg_file: str = None):
        self.nef_file = nef_file
        self.jpg_file = jpg_file
        self.pil = None
        self.info = None
        self.prev = None
        self.next = None

        if self.jpg_file is not None:
            self.pil = Image.open(self.jpg_file)
        elif self.nef_file is not None:
            with rawpy.imread(self.nef_file) as raw:
                thumb = raw.extract_thumb()
                if thumb.format == rawpy.ThumbFormat.JPEG:
                    self.pil = Image.open(io.BytesIO(thumb.data))
                elif thumb.format == rawpy.ThumbFormat.BITMAP:
                    self.pil = Image.fromarray(thumb.data)
                else:
                    raise NotImplementedError(f"Unsupported thumbnail format {str(thumb.format)}")
        else:
            raise ValueError("Neither NEF nor JPEG file is present.")

        if self.jpg_file is not None and self.nef_file is not None:
            self.mode = "NEF + JPG"
            self.filename = str(self.jpg_file + " | " + self.nef_file).replace("\\", "/")
            self.info = f"NEF & JPG : {self.pil.width} x {self.pil.height} {self.pil.mode}"
        elif self.nef_file is not None:
            self.mode = "NEF ONLY"
            self.info = f"NEF : {self.pil.width} x {self.pil.height} {self.pil.mode}"
            self.filename = self.nef_file.replace("\\", "/")
        elif self.jpg_file is not None:
            self.mode = "JPG ONLY"
            self.info = f"JPG : {self.pil.width} x {self.pil.height} {self.pil.mode}"
            self.filename = self.jpg_file.replace("\\", "/")
        else:
            raise ValueError("Neither NEF nor JPEG file is present.")

    def has_nef(self) -> bool:
        return self.nef_file is not None

    def has_jpg(self) -> bool:
        return self.jpg_file is not None

    def close(self):
        if self.pil is not None:
            self.pil.close()
            self.pil = None


class ImageHandler:
    def __init__(self, nef_folder="./NEF", jpg_folder="./JPG", opt_nef_folder="./SEL_NEF", opt_jpg_folder="./SEL_JPG",
                 del_nef_folder="./DEL_NEF", del_jpg_folder="./DEL_JPG"):
        nef_files = glob.glob(os.path.join(nef_folder, '*.NEF'))
        jpg_files = glob.glob(os.path.join(jpg_folder, '*.JPG'))
        os.makedirs(opt_jpg_folder, exist_ok=True)
        os.makedirs(opt_nef_folder, exist_ok=True)
        os.makedirs(del_jpg_folder, exist_ok=True)
        os.makedirs(del_nef_folder, exist_ok=True)
        assert os.path.isdir(opt_nef_folder)
        assert os.path.isdir(opt_jpg_folder)
        assert os.path.isdir(del_nef_folder)
        assert os.path.isdir(del_jpg_folder)
        self._opt_nef_folder = opt_nef_folder
        self._opt_jpg_folder = opt_jpg_folder
        self._del_nef_folder = del_nef_folder
        self._del_jpg_folder = del_jpg_folder

        all_files = sorted(nef_files + jpg_files, key=lambda x: os.path.basename(x))
        self._org_size = 0
        self._curr_size = 0
        self._head = None
        prev = None

        i = 0
        while i < len(all_files):
            jpg_file, nef_file = None, None

            if all_files[i].endswith(".JPG"):
                jpg_file = all_files[i]
            elif all_files[i].endswith(".NEF"):
                nef_file = all_files[i]
            else:
                raise ValueError(f"Unsupported file format {all_files[i]}.")

            if i + 1 < len(all_files) and os.path.basename(all_files[i])[:-4] == os.path.basename(all_files[i + 1])[
                                                                                 :-4]:
                if all_files[i + 1].endswith(".NEF"):
                    assert nef_file is None and jpg_file is not None
                    nef_file = all_files[i + 1]
                elif all_files[i + 1].endswith(".JPG"):
                    assert jpg_file is None and nef_file is not None
                    jpg_file = all_files[i + 1]
                else:
                    raise ValueError(f"Unsupported file format {all_files[i + 1]}.")
                i += 1

            img_obj = ImageObject(nef_file=nef_file, jpg_file=jpg_file)

            if self._head is None:
                self._head = img_obj

            if prev is not None:
                prev.next = img_obj
                img_obj.prev = prev

            prev = img_obj
            i += 1
            self._org_size += 1

        self._curr_size = self._org_size
        self._curr = self._head
        print(f"Successfully read {self._org_size} image objects.")

    def curr_size(self) -> int:
        return self._curr_size

    def org_size(self) -> int:
        return self._org_size

    def curr_img(self) -> Optional[ImageObject, None]:
        return self._curr

    def has_next(self) -> bool:
        return self._curr is not None and self._curr.next is not None

    def has_prev(self) -> bool:
        return self._curr is not None and self._curr.prev is not None

    def next_img(self) -> ImageObject:
        assert self._curr is not None
        if self._curr.next is not None:
            self._curr = self._curr.next
        return self._curr

    def prev_img(self) -> ImageObject:
        assert self._curr is not None
        if self._curr.prev is not None:
            self._curr = self._curr.prev
        return self._curr

    def op_keep_jpg(self):
        assert self._curr is not None
        assert self._curr.has_jpg()
        self._curr.close()
        shutil.move(self._curr.jpg_file, self._opt_jpg_folder)
        if self._curr.has_nef():
            shutil.move(self._curr.nef_file, self._del_nef_folder)
        self._remove_curr()

    def op_keep_nef(self):
        assert self._curr is not None
        assert self._curr.has_nef()
        self._curr.close()
        shutil.move(self._curr.nef_file, self._opt_nef_folder)
        if self._curr.has_jpg():
            shutil.move(self._curr.jpg_file, self._del_jpg_folder)
        self._remove_curr()

    def _remove_curr(self) -> Optional[ImageObject]:
        assert self._curr is not None
        aft = self._curr.next if self._curr.next is not None else self._curr.prev

        if self._curr == self._head:
            self._head = self._curr.next

        if self._curr.prev is not None:
            self._curr.prev.next = self._curr.next

        if self._curr.next is not None:
            self._curr.next.prev = self._curr.prev

        self._curr.prev = None
        self._curr.next = None
        self._curr = aft
        self._curr_size -= 1
        return aft
