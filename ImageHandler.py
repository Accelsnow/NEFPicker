from __future__ import annotations
from typing import Optional
import io
import os
import sys
import glob
import rawpy
import exiftool
import fractions
from datetime import datetime
from PIL import Image
from CTkMessagebox import CTkMessagebox


def disp_error(msg: str, exit_after: bool = False):
    msg = CTkMessagebox(title="Error", message=msg, icon="cancel")
    msg.get()
    if exit_after:
        sys.exit(1)


def read_meta(file: str):
    with exiftool.ExifToolHelper() as et:
        metadata = et.get_metadata([file])

        shutter = ""
        if "EXIF:ExposureTime" in metadata[0]:
            ss = float(metadata[0]["EXIF:ExposureTime"])
            shutter = str(fractions.Fraction(ss).limit_denominator())
            if ss >= 1:
                shutter += '"'

        aper = f"f/{metadata[0]['EXIF:FNumber']}" if "EXIF:FNumber" in metadata[0] else ""
        iso = f"ISO{metadata[0]['EXIF:ISO']}" if "EXIF:ISO" in metadata[0] else ""
        ev = f"{metadata[0]['EXIF:ExposureCompensation']}EV" if "EXIF:ExposureCompensation" in metadata[0] else ""
        foc = f"{metadata[0]['EXIF:FocalLength']}mm" if "EXIF:FocalLength" in metadata[0] else ""
        date_str = datetime.strptime(metadata[0]["EXIF:DateTimeOriginal"],
                                     "%Y:%m:%d %H:%M:%S") if "EXIF:DateTimeOriginal" in metadata[0] else ""
        lens = f"{metadata[0]['EXIF:LensModel']}" if "EXIF:LensModel" in metadata[0] else ""
        return {
            "shutter": shutter,
            "aper": aper,
            "iso": iso,
            "ev": ev,
            "foc": foc,
            "date": date_str,
            "lens": lens,
        }


class ImageObject:
    def __init__(self, nef_file: str = None, jpg_file: str = None):
        self._valid = False
        self.nef_file = nef_file
        self.jpg_file = jpg_file
        self.pil = None
        self.meta = None
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
                    msg = CTkMessagebox(title="Unknown NEF Thumb Format",
                                        message=f"Unsupported thumbnail format {str(thumb.format)} in NEF file: {self.nef_file}.",
                                        icon="warning", option_1="Exit", option_2="Continue")
                    if msg.get() == "Exit":
                        sys.exit(1)
                    return
        else:
            raise ValueError("Neither NEF nor JPEG file is present.")

        if self.nef_file is not None:
            self.meta = read_meta(self.nef_file)
        elif self.jpg_file is not None:
            self.meta = read_meta(self.jpg_file)
        else:
            raise ValueError("Neither NEF nor JPEG file is present.")

        self.info = f"{self.meta['shutter']}  |  {self.meta['aper']}  |  {self.meta['iso']}  |  {self.meta['ev']}  |  {self.meta['foc']}  |  {self.meta['lens']}  |  {self.meta['date']}  |  {self.pil.width} x {self.pil.height} {self.pil.mode}"

        if self.jpg_file is not None and self.nef_file is not None:
            self.mode = "NEF + JPG"
            self.info = f"NEF & JPG : " + self.info
            self.filename = str(self.jpg_file + " | " + self.nef_file).replace("\\", "/")
        elif self.nef_file is not None:
            self.mode = "NEF ONLY"
            self.info = f"NEF : " + self.info
            self.filename = self.nef_file.replace("\\", "/")
        elif self.jpg_file is not None:
            self.mode = "JPG ONLY"
            self.info = f"JPG : " + self.info
            self.filename = self.jpg_file.replace("\\", "/")
        else:
            raise ValueError("Neither NEF nor JPEG file is present.")

        self._valid = True

    def has_nef(self) -> bool:
        return self.nef_file is not None

    def has_jpg(self) -> bool:
        return self.jpg_file is not None

    def is_valid(self) -> bool:
        return self._valid

    def close(self):
        if self.pil is not None:
            self.pil.close()
            self.pil = None
        return self._valid


def is_jpg_file(filename: str) -> bool:
    return filename.upper().endswith(".JPG") or filename.upper().endswith(".JPEG")


def is_nef_file(filename: str) -> bool:
    return filename.upper().endswith(".NEF")


def no_ext_fname(path: str) -> str:
    return ".".join(os.path.basename(path).split(".")[:-1])


class ImageHandler:
    def __init__(self, nef_folder="./NEF", jpg_folder="./JPG", opt_nef_folder="./SEL_NEF", opt_jpg_folder="./SEL_JPG",
                 del_folder="./DEL"):
        nef_files = [f for f in glob.glob(os.path.join(nef_folder, '*')) if is_nef_file(f)]
        jpg_files = [f for f in glob.glob(os.path.join(jpg_folder, '*')) if is_jpg_file(f)]
        os.makedirs(opt_jpg_folder, exist_ok=True)
        os.makedirs(opt_nef_folder, exist_ok=True)
        os.makedirs(del_folder, exist_ok=True)
        assert os.path.isdir(opt_nef_folder)
        assert os.path.isdir(opt_jpg_folder)
        assert os.path.isdir(del_folder)
        self._opt_nef_folder = opt_nef_folder
        self._opt_jpg_folder = opt_jpg_folder
        self._del_folder = del_folder

        all_files = sorted(nef_files + jpg_files, key=lambda x: os.path.basename(x))
        self._org_size = 0
        self._curr_size = 0
        self._head = None
        prev = None

        i = 0
        while i < len(all_files):
            jpg_file, nef_file = None, None
            istep = 1

            if is_jpg_file(all_files[i]):
                jpg_file = all_files[i]
            elif is_nef_file(all_files[i]):
                nef_file = all_files[i]
            else:
                raise ValueError(f"Unsupported file format {all_files[i]}.")

            if i + 1 < len(all_files) and no_ext_fname(all_files[i]) == no_ext_fname(all_files[i + 1]):
                if is_nef_file(all_files[i + 1]):
                    assert nef_file is None and jpg_file is not None
                    nef_file = all_files[i + 1]
                elif is_jpg_file(all_files[i + 1]):
                    assert jpg_file is None and nef_file is not None
                    jpg_file = all_files[i + 1]
                else:
                    raise ValueError(f"Unsupported file format {all_files[i + 1]}.")
                istep = 2

            img_obj = ImageObject(nef_file=nef_file, jpg_file=jpg_file)

            if not img_obj.is_valid():
                i += 1
                continue

            if self._head is None:
                self._head = img_obj

            if prev is not None:
                prev.next = img_obj
                img_obj.prev = prev

            prev = img_obj
            i += istep
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

    def _rename_mv(self, src_file: str, dest_folder: str):
        while True:
            try:
                if 'date' in self._curr.meta and self._curr.meta['date']:
                    success = False
                    for i in range(1, 50):
                        if i <= 1:
                            new_filename = f"IMG_{self._curr.meta['date'].strftime('%y%m%d_%H%M%S')}.{src_file.split('.')[-1]}"
                        else:
                            new_filename = f"IMG_{self._curr.meta['date'].strftime('%y%m%d_%H%M%S')}({i}).{src_file.split('.')[-1]}"

                        if os.path.exists(os.path.join(dest_folder, new_filename)):
                            continue

                        os.rename(src_file, os.path.join(dest_folder, new_filename))
                        success = True
                        break

                    if not success:
                        os.rename(src_file, dest_folder)
                else:
                    os.rename(src_file, dest_folder)

                break
            except Exception as e:
                msg = CTkMessagebox(title="Error",
                                    message=f"Unable to move file {src_file} to {dest_folder}.\n{str(e)}",
                                    option_1="Skip", option_2="Retry", icon="cancel")
                if msg.get() == "Retry":
                    continue
                else:
                    break

    def op_keep_jpg(self):
        assert self._curr is not None
        assert self._curr.has_jpg()
        self._curr.close()
        self._rename_mv(self._curr.jpg_file, self._opt_jpg_folder)
        if self._curr.has_nef():
            self._rename_mv(self._curr.nef_file, self._del_folder)
        self._remove_curr()

    def op_keep_nef(self):
        assert self._curr is not None
        assert self._curr.has_nef()
        self._curr.close()
        self._rename_mv(self._curr.nef_file, self._opt_nef_folder)
        if self._curr.has_jpg():
            self._rename_mv(self._curr.jpg_file, self._del_folder)
        self._remove_curr()

    def op_del_both(self):
        assert self._curr is not None
        self._curr.close()
        if self._curr.has_nef():
            self._rename_mv(self._curr.nef_file, self._del_folder)
        if self._curr.has_jpg():
            self._rename_mv(self._curr.jpg_file, self._del_folder)
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
