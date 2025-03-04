# Copyright 2025 Akira
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Modifications by Adrian Zhao on 2025-03-04

from __future__ import annotations
import math
import numpy as np
import customtkinter as ctk
from PIL import Image, ImageTk
from CTkMessagebox import CTkMessagebox
from ImageHandler import ImageHandler, ImageObject

class ImageViewer(ctk.CTk):
    def __init__(self, nef_folder="./NEF", jpg_folder="./JPG", opt_nef_folder="./SEL_NEF", opt_jpg_folder="./SEL_JPG",
                 del_nef_folder="./DEL_NEF", del_jpg_folder="./DEL_JPG"):
        super().__init__()

        print("Reading all images ...")
        self.img_it = ImageHandler(nef_folder, jpg_folder, opt_nef_folder, opt_jpg_folder, del_nef_folder,
                                   del_jpg_folder)

        if not self.img_it.has_next():
            raise ValueError("No image available.")

        print("Image read complete!")

        self.geometry("1280x720")

        self.image = None
        self.pil_image = None  # 表示する画像データ
        self.my_title = "Python Image Viewer"

        # ウィンドウの設定
        self.title(self.my_title)

        # 実行内容

        self._create_widget()  # ウィジェットの作成

        self.mat_affine = np.eye(3)

        # 初期アフィン変換行列
        self.reset_transform()

        self.__old_event = None

        self.after(100, lambda: (self.set_image(self.img_it.curr_img()), self.update_buttons()))

    # create_widgetメソッドを定義
    def _create_widget(self):
        frame_ctrl = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        frame_ctrl.grid_rowconfigure(0, weight=1)
        frame_ctrl.grid_columnconfigure(0, weight=1)

        self.button_prev = ctk.CTkButton(frame_ctrl, text="<< Prev", anchor=ctk.W, command=self.show_prev,
                                         state=ctk.DISABLED)
        self.button_prev.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        self.button_keep_jpg = ctk.CTkButton(frame_ctrl, text="Keep JPG", anchor=ctk.CENTER, command=self.keep_jpg, state=ctk.DISABLED)
        self.button_keep_jpg.grid(row=0, column=1, padx=20, pady=20, sticky="w")

        self.button_keep_nef = ctk.CTkButton(frame_ctrl, text="Keep NEF", anchor=ctk.CENTER, command=self.keep_nef, state=ctk.DISABLED)
        self.button_keep_nef.grid(row=0, column=2, padx=20, pady=20, sticky="w")

        self.button_next = ctk.CTkButton(frame_ctrl, text=">> Next", anchor=ctk.E, command=self.show_next,
                                         state=ctk.NORMAL)
        self.button_next.grid(row=0, column=3, padx=20, pady=20, sticky="e")

        frame_ctrl.pack(side=ctk.BOTTOM, fill=ctk.X)

        # ステータスバー相当(親に追加)
        frame_statusbar = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.label_image_info = ctk.CTkLabel(frame_statusbar, text="image info", anchor=ctk.E, padx=5)
        self.label_image_pixel = ctk.CTkLabel(frame_statusbar, text="(x, y)", anchor=ctk.W, padx=5)
        self.label_image_info.pack(side=ctk.RIGHT)
        self.label_image_pixel.pack(side=ctk.LEFT)
        frame_statusbar.pack(side=ctk.BOTTOM, fill=ctk.X)

        # Canvas
        self.canvas = ctk.CTkCanvas(self, background="black")
        self.canvas.pack(expand=True, fill=ctk.BOTH)  # この両方でDock.Fillと同じ

        # マウスイベント
        self.bind("<Button-1>", self.mouse_down_left)  # MouseDown
        self.bind("<B1-Motion>", self.mouse_move_left)  # MouseDrag（ボタンを押しながら移動）
        self.bind("<Motion>", self.mouse_move)  # MouseMove
        self.bind("<Double-Button-1>", self.mouse_double_click_left)  # MouseDoubleClick
        self.bind("<MouseWheel>", self.mouse_wheel)  # MouseWheel

    def show_prev(self):
        self.set_image(self.img_it.prev_img())
        self.update_buttons()

    def show_next(self):
        self.set_image(self.img_it.next_img())
        self.update_buttons()

    def keep_jpg(self):
        self.pil_image = None
        self.img_it.op_keep_jpg()
        if self.img_it.curr_img() is None:
            msg = CTkMessagebox(title="Info", message="All images processed!", icon="info")
            # CTkMessagebox(title="Error", message="Something went wrong!!!", icon="cancel")
            if msg.get():
                self.quit()
        else:
            self.set_image(self.img_it.curr_img())
            self.update_buttons()

    def keep_nef(self):
        self.pil_image = None
        self.img_it.op_keep_nef()
        if self.img_it.curr_img() is None:
            msg = CTkMessagebox(title="Info", message="All images processed!", icon="info")
            # CTkMessagebox(title="Error", message="Something went wrong!!!", icon="cancel")
            if msg.get():
                self.quit()
        else:
            self.set_image(self.img_it.curr_img())
            self.update_buttons()

    def update_buttons(self):
        if not self.img_it.has_prev():
            self.button_prev.configure(state=ctk.DISABLED)
        else:
            self.button_prev.configure(state=ctk.NORMAL)

        if not self.img_it.has_next():
            self.button_next.configure(state=ctk.DISABLED)
        else:
            self.button_next.configure(state=ctk.NORMAL)

        if not self.img_it.curr_img().has_jpg():
            self.button_keep_jpg.configure(state=ctk.DISABLED)
        else:
            self.button_keep_jpg.configure(state=ctk.NORMAL)

        if not self.img_it.curr_img().has_nef():
            self.button_keep_nef.configure(state=ctk.DISABLED)
        else:
            self.button_keep_nef.configure(state=ctk.NORMAL)

    def set_image(self, img_obj: ImageObject):
        # PIL.Imageで開く
        self.pil_image = img_obj.pil
        # 画像全体に表示するようにアフィン変換行列を設定
        self.zoom_fit(self.pil_image.width, self.pil_image.height)
        # 画像の表示
        self.draw_image()

        # ウィンドウタイトルのファイル名を設定
        self.title(img_obj.filename)
        # ステータスバーに画像情報を表示する
        self.label_image_info.configure(text=img_obj.info)

    # -------------------------------------------------------------------------------
    # マウスイベント
    # -------------------------------------------------------------------------------
    def mouse_down_left(self, event):
        """ マウスの左ボタンを押した """
        self.__old_event = event

    def mouse_move_left(self, event):
        """ マウスの左ボタンをドラッグ """
        if self.pil_image is None:
            return
        self.translate(event.x - self.__old_event.x, event.y - self.__old_event.y)
        self.draw_image()  # 再描画
        self.__old_event = event

    def mouse_move(self, event):
        """ マウスの左ボタンをドラッグ """
        if self.pil_image is None:
            return
        image_point = self.to_image_point(event.x, event.y)
        if len(image_point) > 0:
            self.label_image_pixel.configure(text=f"({image_point[0]:.2f}, {image_point[1]:.2f})")
        else:
            self.label_image_pixel.configure(text="(--, --)")

    def mouse_double_click_left(self, event):
        """ マウスの左ボタンをダブルクリック """
        if self.pil_image is None:
            return
        self.zoom_fit(self.pil_image.width, self.pil_image.height)
        self.draw_image()  # 再描画

    def mouse_wheel(self, event):
        """ マウスホイールを回した """
        if self.pil_image is None:
            return

        if event.state != 9:  # 9はShiftキー(Windowsの場合だけかも？)
            if event.delta < 0:
                # 下に回転の場合、縮小
                self.scale_at(0.8, event.x, event.y)
            else:
                # 上に回転の場合、拡大
                self.scale_at(1.25, event.x, event.y)
        else:
            if event.delta < 0:
                # 下に回転の場合、反時計回り
                self.rotate_at(-5, event.x, event.y)
            else:
                # 上に回転の場合、時計回り
                self.rotate_at(5, event.x, event.y)
        self.draw_image()  # 再描画

    # -------------------------------------------------------------------------------
    # 画像表示用アフィン変換
    # -------------------------------------------------------------------------------

    def reset_transform(self):
        """アフィン変換を初期化（スケール１、移動なし）に戻す"""
        self.mat_affine = np.eye(3)  # 3x3の単位行列

    def translate(self, offset_x, offset_y):
        """ 平行移動 """
        mat = np.eye(3)  # 3x3の単位行列
        mat[0, 2] = float(offset_x)
        mat[1, 2] = float(offset_y)

        self.mat_affine = np.dot(mat, self.mat_affine)

    def scale(self, scale: float):
        """ 拡大縮小 """
        mat = np.eye(3)  # 単位行列
        mat[0, 0] = scale
        mat[1, 1] = scale

        self.mat_affine = np.dot(mat, self.mat_affine)

    def scale_at(self, scale: float, cx: float, cy: float):
        """ 座標(cx, cy)を中心に拡大縮小 """

        # 原点へ移動
        self.translate(-cx, -cy)
        # 拡大縮小
        self.scale(scale)
        # 元に戻す
        self.translate(cx, cy)

    def rotate(self, deg: float):
        """ 回転 """
        mat = np.eye(3)  # 単位行列
        mat[0, 0] = math.cos(math.pi * deg / 180)
        mat[1, 0] = math.sin(math.pi * deg / 180)
        mat[0, 1] = -mat[1, 0]
        mat[1, 1] = mat[0, 0]

        self.mat_affine = np.dot(mat, self.mat_affine)

    def rotate_at(self, deg: float, cx: float, cy: float):
        """ 座標(cx, cy)を中心に回転 """

        # 原点へ移動
        self.translate(-cx, -cy)
        # 回転
        self.rotate(deg)
        # 元に戻す
        self.translate(cx, cy)

    def zoom_fit(self, image_width, image_height):
        """画像をウィジェット全体に表示させる"""

        # キャンバスのサイズ
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if (image_width * image_height <= 0) or (canvas_width * canvas_height <= 0):
            return

        # アフィン変換の初期化
        self.reset_transform()

        scale = 1.0
        offsetx = 0.0
        offsety = 0.0

        if (canvas_width * image_height) > (image_width * canvas_height):
            # ウィジェットが横長（画像を縦に合わせる）
            scale = canvas_height / image_height
            # あまり部分の半分を中央に寄せる
            offsetx = (canvas_width - image_width * scale) / 2
        else:
            # ウィジェットが縦長（画像を横に合わせる）
            scale = canvas_width / image_width
            # あまり部分の半分を中央に寄せる
            offsety = (canvas_height - image_height * scale) / 2

        # 拡大縮小
        self.scale(scale)
        # あまり部分を中央に寄せる
        self.translate(offsetx, offsety)

    def to_image_point(self, x, y):
        """　キャンバスの座標から画像の座標へ変更 """
        if self.pil_image is None:
            return []
        # 画像→キャンバスの変換からキャンバス→画像にする（逆行列にする）
        mat_inv = np.linalg.inv(self.mat_affine)
        image_point = np.dot(mat_inv, (x, y, 1.))
        if image_point[0] < 0 or image_point[1] < 0 or image_point[0] > self.pil_image.width or image_point[
            1] > self.pil_image.height:
            return []

        return image_point

    # -------------------------------------------------------------------------------
    # 描画
    # -------------------------------------------------------------------------------

    def draw_image(self):
        if self.pil_image is None:
            return

        # キャンバスのサイズ
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # キャンバスから画像データへのアフィン変換行列を求める
        # （表示用アフィン変換行列の逆行列を求める）
        mat_inv = np.linalg.inv(self.mat_affine)

        # numpy arrayをアフィン変換用のタプルに変換
        affine_inv = (
            mat_inv[0, 0], mat_inv[0, 1], mat_inv[0, 2],
            mat_inv[1, 0], mat_inv[1, 1], mat_inv[1, 2]
        )

        # PILの画像データをアフィン変換する
        dst = self.pil_image.transform(
            (canvas_width, canvas_height),  # 出力サイズ
            Image.AFFINE,  # アフィン変換
            affine_inv,  # アフィン変換行列（出力→入力への変換行列）
            Image.NEAREST  # 補間方法、ニアレストネイバー
        )

        im = ImageTk.PhotoImage(image=dst)

        # 画像の描画
        _ = self.canvas.create_image(
            0, 0,  # 画像表示位置(左上の座標)
            anchor='nw',  # アンカー、左上が原点
            image=im  # 表示画像データ
        )

        self.image = im